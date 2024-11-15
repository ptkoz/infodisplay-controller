from domain_types import DeviceKind, OperatingMode
from persistence.models import ThresholdTemperature
from ._AbstractRepository import AbstractRepository


class ThresholdTemperatureRepository(AbstractRepository):
    """
    Repository for managing persisted threshold temperatures
    """

    def set_threshold_temperature(
        self,
        device_kind: DeviceKind,
        operating_mode: OperatingMode,
        temperature: float
    ) -> ThresholdTemperature:
        """
        Sets threshold temperature for given device and operating mode
        """
        threshold_temperature = self.get_threshold_temperature(device_kind, operating_mode)
        threshold_temperature.temperature_centi = round(temperature * 100)

        return threshold_temperature

    def get_threshold_temperature(self, device_kind: DeviceKind, operating_mode: OperatingMode) -> ThresholdTemperature:
        """
        Returns the configured threshold temperature for given device and operating mode
        """
        threshold_temperature = (
            self
            ._session
            .query(ThresholdTemperature)
            .filter(ThresholdTemperature.device_kind == device_kind)
            .filter(ThresholdTemperature.operating_mode == operating_mode)
            .first()
        )

        if threshold_temperature is None:
            threshold_temperature = ThresholdTemperature(
                device_kind,
                operating_mode,
                self.__get_default_temperature(device_kind)
            )

            self._session.add(threshold_temperature)

        return threshold_temperature

    def __get_default_temperature(self, device_kind: DeviceKind) -> int:
        """
        Returns default temperature for given device kind
        """
        if device_kind == DeviceKind.COOLING:
            return 2600

        return 1700
