import logging
from persistence import SensorMeasure, SensorMeasureRepository
from ui import TemperatureUpdate, HumidityUpdate
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class SaveMeasure(AbstractCommand):
    """
    A command that saves the received measure into the database and publishes it to UI
    """

    def __init__(self, measure: SensorMeasure):
        self.measure = measure

    def execute(self, context: ExecutionContext) -> None:
        """
        Executes the command
        """
        logging.debug(
            "Saving measure kind: %s, t: %.2f, h: %.2f, v: %.2f",
            self.measure.kind.name,
            self.measure.temperature,
            self.measure.humidity or 0,
            self.measure.voltage or 0
        )

        SensorMeasureRepository(context.db_session).create(self.measure)

        context.publisher.publish(
            TemperatureUpdate(self.measure.timestamp, self.measure.kind, self.measure.temperature)
        )
        if self.measure.humidity is not None:
            context.publisher.publish(HumidityUpdate(
                self.measure.timestamp, self.measure.kind, self.measure.humidity)
            )
