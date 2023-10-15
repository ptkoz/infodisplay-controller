from persistence import SensorMeasure, TemperatureRegulationRepository
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
        for (device_kind, target_temperature) in regulations:
            context.command_queue.put_nowait(
                RegulateTemperature(device_kind, self.measure, target_temperature)
            )
