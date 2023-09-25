from datetime import datetime
from typing import Optional
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from domain_types import MeasureKind
from .AbstractBase import AbstractBase


class SensorMeasure(AbstractBase):
    """
    Represents a measurement from a sensor
    """

    __tablename__ = "sensor_measure"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime]
    kind: Mapped[MeasureKind]
    temperature: Mapped[float]
    humidity: Mapped[float] = mapped_column(nullable=True)
    voltage: Mapped[float] = mapped_column(nullable=True)

    __table_args__ = (
        Index('sensor_measure_by_kind_idx', "kind", "timestamp"),
    )

    def __init__(
        self,
        timestamp: datetime,
        kind: MeasureKind,
        temperature: float,
        humidity: Optional[float] = None,
        voltage: Optional[float] = None
    ):
        super().__init__(timestamp=timestamp, kind=kind, temperature=temperature, humidity=humidity, voltage=voltage)
