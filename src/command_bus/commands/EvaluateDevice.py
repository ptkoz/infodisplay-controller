from datetime import timedelta

from domain_types import DeviceKind
from persistence import DeviceControlRepository, SensorMeasureRepository
from .AbstractCommand import AbstractCommand
from .EvaluateDeviceAgainstMeasure import EvaluateDeviceAgainstMeasure
from ..ExecutionContext import ExecutionContext


class EvaluateDevice(AbstractCommand):
    """
    A command that queues device evaluation for all measures that are controlling given device
    """

    def __init__(self, kind: DeviceKind):
        self.kind = kind

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        measure_repository = SensorMeasureRepository(context.db_session)
        device_control_repository = DeviceControlRepository(context.db_session)
        operating_mode = device_control_repository.get_mode_for(context.time_source.now())

        for device_control in device_control_repository.get_measures_controlling(self.kind, operating_mode):
            measure = measure_repository.get_last_temperature(
                device_control.measure_kind,
                context.time_source.now() - timedelta(minutes=10)
            )

            if measure is not None:
                context.command_queue.put_nowait(
                    EvaluateDeviceAgainstMeasure(self.kind, operating_mode, measure)
                )
