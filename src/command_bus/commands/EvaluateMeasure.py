from datetime import timedelta
from domain_types import DeviceKind
from persistence import DeviceControlRepository, SensorMeasure, SensorMeasureRepository, TemperatureRegulationRepository
from .AbstractCommand import AbstractCommand
from .RegulateTemperature import RegulateTemperature
from ..ExecutionContext import ExecutionContext


class EvaluateMeasure(AbstractCommand):
    """
    A command that queues device evaluation for any device controlled by given measure
    """

    def __init__(self, measure: SensorMeasure):
        self.measure = measure

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        regulations = (
            TemperatureRegulationRepository(context.db_session)
            .get_regulation_for_measure(self.measure.kind, context.time_source)
        )

        for (device_kind, threshold_temperature) in regulations:
            # If there are multiple measures controlling single device, only consider the one with the lowest reading
            if not self.has_lower_measure_from_other_sensors(context, device_kind):
                context.command_queue.put_nowait(
                    RegulateTemperature(device_kind, self.measure, threshold_temperature)
                )

    def has_lower_measure_from_other_sensors(self, context: ExecutionContext, device_kind: DeviceKind):
        """
        Checks whether there are any recent measures from sensor other than then one which sources currently evaluated
        temperature. If so, we should not evaluate it to avoid turn-on / turn-off ping pong.
        """
        device_control_repository = DeviceControlRepository(context.db_session)
        measure_repository = SensorMeasureRepository(context.db_session)
        mode = device_control_repository.get_mode_for(context.time_source.now())
        measures = device_control_repository.get_measures_controlling(device_kind, mode)

        for device_control in measures:
            if device_control.measure_kind == self.measure.kind:
                # skip the measure that is currently evaluated
                continue

            measure = measure_repository.get_last_temperature(
                device_control.measure_kind,
                context.time_source.now() - timedelta(minutes=10)
            )

            if measure is not None and measure.temperature < self.measure.temperature:
                return True

        return False
