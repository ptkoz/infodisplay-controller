import logging
from datetime import datetime
from typing import Optional
from persistence import SensorMeasureRepository
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class SaveMeasure(AbstractCommand):
    """
    A command that saves the received measure into the database
    """

    def __init__(
        self,
        timestamp: datetime,
        kind: int,
        temperature: float,
        humidity: Optional[float] = None,
        voltage: Optional[float] = None
    ):
        self.kind = kind
        self.timestamp = timestamp
        self.temperature = temperature
        self.humidity = humidity
        self.voltage = voltage

    def execute(self, context: ExecutionContext) -> None:
        """
        Executes the command
        """
        logging.debug(
            "Saving measure kind: %#x, t: %.2f, h: %.2f, v: %.2f",
            self.kind,
            self.temperature,
            self.humidity or 0,
            self.voltage or 0
        )

        SensorMeasureRepository(context.db_session).create(
            self.timestamp,
            self.kind,
            self.temperature,
            self.humidity,
            self.voltage
        )
