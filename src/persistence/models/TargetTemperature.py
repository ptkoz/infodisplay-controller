from sqlalchemy.orm import Mapped, mapped_column
from domain_types import DeviceKind, OperatingMode
from .AbstractBase import AbstractBase


class TargetTemperature(AbstractBase):
    """
    Represents configured target temperature for given device and operating mode
    """
    __tablename__ = "target_temperature"
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
