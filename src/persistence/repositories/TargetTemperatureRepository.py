from persistence.models import TargetTemperature
from ._AbstractRepository import AbstractRepository


class TargetTemperatureRepository(AbstractRepository):
    """
    Repository for managing persisted target temperature
    """

    def get_target_temperature(self) -> TargetTemperature:
        """
        Returns the configured target temperature
        """
        target_temperature = self._session.query(TargetTemperature).filter(TargetTemperature.id == 1).first()

        if target_temperature is None:
            target_temperature = TargetTemperature(1, 2350)

            self._session.add(target_temperature)
            self._session.commit()

        return target_temperature
