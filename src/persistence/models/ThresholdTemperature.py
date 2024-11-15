from sqlalchemy.orm import Mapped, mapped_column
from domain_types import DeviceKind, OperatingMode
from .AbstractBase import AbstractBase


class ThresholdTemperature(AbstractBase):
    """
    Represents configured threshold temperature for given device and operating mode.
    """
    __tablename__ = "threshold_temperature"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_kind: Mapped[DeviceKind]
    operating_mode: Mapped[OperatingMode]
    temperature_centi: Mapped[int]

    def __init__(self, device_kind: DeviceKind, operating_mode: OperatingMode, temperature_centi: int):
        super().__init__(device_kind=device_kind, operating_mode=operating_mode, temperature_centi=temperature_centi)

    @property
    def temperature(self) -> float:
        """
        Returns float representation of the temperature
        :return:
        """
        return self.temperature_centi / 100

    @property
    def warm_up_threshold(self) -> float:
        """
        Returns the threshold below which we should start warming up
        """
        match self.device_kind:
            case DeviceKind.COOLING:
                # Cooling turns off when temperature drops RANGE below configured max temp
                return self.temperature - self.__temperature_range
            case DeviceKind.HEATING:
                # Heating turns on when temperature drops to configured min temp
                return self.temperature
            case _:
                # Otherwise we consider the temp to be in the middle of the range
                return self.temperature - (self.__temperature_range / 2)

    @property
    def cool_down_threshold(self) -> float:
        """
        Return threshold above which we should start cooling down
        """
        match self.device_kind:
            case DeviceKind.COOLING:
                # Cooling turns on when temperature rises to configured max temp
                return self.temperature
            case DeviceKind.HEATING:
                # Heating turns off when temperature raises RANGE above configured min temp
                return self.temperature + self.__temperature_range
            case _:
                # Otherwise we consider the temp to be in the middle of the range
                return self.temperature + (self.__temperature_range / 2)

    @property
    def __temperature_range(self) -> float:
        """
        Returns the tolerance for the temperature
        """
        return 0.5
