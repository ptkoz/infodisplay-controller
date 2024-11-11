from datetime import datetime
from typing import Optional
from persistence.models import SensorMeasure
from domain_types import MeasureKind
from ._AbstractRepository import AbstractRepository


class SensorMeasureRepository(AbstractRepository):
    """
    Repository for persisting sensor measures
    """

    def create(self, measure: SensorMeasure):
        """
        Creates a new measurement record
        """
        self._session.add(measure)
        return measure

    def get_last_temperature(self, kind: MeasureKind, max_age: Optional[datetime] = None) -> Optional[SensorMeasure]:
        """
        Returns the last temperature of given kind
        """
        query = self._session.query(SensorMeasure).filter(SensorMeasure.kind == kind)

        if max_age is not None:
            query = query.filter(SensorMeasure.timestamp > max_age)

        return query.order_by(SensorMeasure.timestamp.desc()).first()

    def get_last_below(self, kind: MeasureKind, temperature: float):
        """
        Returns the last temperature below given value
        """
        return self._session.query(SensorMeasure).filter(
            SensorMeasure.kind == kind
        ).filter(
            SensorMeasure.temperature < temperature
        ).order_by(SensorMeasure.timestamp.desc()).first()

    def get_last_above(self, kind: MeasureKind, temperature: float):
        """
        Returns the last temperature above given value
        """
        return self._session.query(SensorMeasure).filter(
            SensorMeasure.kind == kind
        ).filter(
            SensorMeasure.temperature > temperature
        ).order_by(SensorMeasure.timestamp.desc()).first()
