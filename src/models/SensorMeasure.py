from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from .AbstractBase import AbstractBase


class SensorMeasure(AbstractBase):
    """
    Represents a measurement from a sensor
    """

    # Available measure kinds
    OUTDOOR = 0x41
    LIVING_ROOM = 0x20
    BEDROOM = 0x21

    __tablename__ = "sensor_measure"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(index=True)
    kind: Mapped[int] = mapped_column(index=True)
    temperature: Mapped[float]
    humidity: Mapped[float] = mapped_column(nullable=True)
    voltage: Mapped[float] = mapped_column(nullable=True)

    def __init__(
        self,
        timestamp: datetime,
        kind: int,
        temperature: float,
        humidity: Optional[float] = None,
        voltage: Optional[float] = None
    ):
        super().__init__(timestamp=timestamp, kind=kind, temperature=temperature, humidity=humidity, voltage=voltage)
