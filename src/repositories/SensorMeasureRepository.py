from datetime import datetime
from typing import Optional
from models import SensorMeasure
from ._AbstractRepository import AbstractRepository


class SensorMeasureRepository(AbstractRepository):
    """
    Repository for persisting sensor measures
    """

    def create(
        self,
        timestamp: datetime,
        kind: int,
        temperature: float,
        humidity: Optional[float] = None,
        voltage: Optional[float] = None
    ):
        """
        Creates a new measurement record
        """
        measure = SensorMeasure(timestamp, kind, temperature, humidity, voltage)
        self._session.add(measure)
        self._session.commit()
        return measure

    def get_last_temperature(self, kind: int, max_age: datetime) -> Optional[SensorMeasure]:
        """
        Returns the last temperature of given kind
        """
        return (
            self._session
            .query(SensorMeasure)
            .filter(SensorMeasure.kind == kind)
            .filter(SensorMeasure.timestamp > max_age)
            .order_by(SensorMeasure.timestamp.desc())
            .first()
        )
