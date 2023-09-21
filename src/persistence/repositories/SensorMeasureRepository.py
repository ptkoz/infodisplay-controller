from datetime import datetime
from typing import Optional
from persistence.models import SensorMeasure
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

    def get_last_temperature(self, kind: int, max_age: Optional[datetime] = None) -> Optional[SensorMeasure]:
        """
        Returns the last temperature of given kind
        """
        query = self._session.query(SensorMeasure).filter(SensorMeasure.kind == kind)

        if max_age is not None:
            query = query.filter(SensorMeasure.timestamp > max_age)

        return query.order_by(SensorMeasure.timestamp.desc()).first()
