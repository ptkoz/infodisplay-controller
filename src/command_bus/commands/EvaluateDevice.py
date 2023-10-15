from datetime import timedelta
from domain_types import DeviceKind
from persistence import TemperatureRegulationRepository, SensorMeasureRepository
from .AbstractCommand import AbstractCommand
from .RegulateTemperature import RegulateTemperature
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
        regulations = (
            TemperatureRegulationRepository(context.db_session)
            .get_regulation_for_device(self.kind, context.time_source)
        )
        for (measure_kind, target_temperature) in regulations:
            measure = measure_repository.get_last_temperature(
                measure_kind,
                context.time_source.now() - timedelta(minutes=10)
            )

            if measure is not None:
                context.command_queue.put_nowait(
                    RegulateTemperature(self.kind, measure, target_temperature)
                )
