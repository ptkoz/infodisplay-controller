from domain_types import DeviceKind, OperatingMode
from persistence.models import TargetTemperature
from ._AbstractRepository import AbstractRepository


class TargetTemperatureRepository(AbstractRepository):
    """
    Repository for managing persisted target temperature
    """

    def set_target_temperature(
        self,
        device_kind: DeviceKind,
        operating_mode: OperatingMode,
        temperature: float
    ) -> TargetTemperature:
        """
        Sets target temperature for given device and operating mode
        """
        target_temperature = self.get_target_temperature(device_kind, operating_mode)
        target_temperature.temperature_centi = round(temperature * 100)

        return target_temperature

    def get_target_temperature(self, device_kind: DeviceKind, operating_mode: OperatingMode) -> TargetTemperature:
        """
        Returns the configured target temperature for given device and operating mode
        """
        target_temperature = (
            self
            ._session
            .query(TargetTemperature)
            .filter(TargetTemperature.device_kind == device_kind)
            .filter(TargetTemperature.operating_mode == operating_mode)
            .first()
        )

        if target_temperature is None:
            target_temperature = TargetTemperature(
                device_kind,
                operating_mode,
                self.__get_default_temperature(device_kind)
            )

            self._session.add(target_temperature)

        return target_temperature

    def __get_default_temperature(self, device_kind: DeviceKind) -> int:
        """
        Returns default temperature for given device kind
        """
        if device_kind == DeviceKind.COOLING:
            return 2600

        return 1700
