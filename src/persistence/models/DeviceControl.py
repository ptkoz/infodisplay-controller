from sqlalchemy.orm import Mapped, mapped_column
from domain_types import DeviceKind, MeasureKind, OperatingMode
from .AbstractBase import AbstractBase


class DeviceControl(AbstractBase):
    """
    Holds information about which measure controls which device
    """
    __tablename__ = "device_control"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_kind: Mapped[DeviceKind]
    measure_kind: Mapped[MeasureKind]
    operating_mode: Mapped[OperatingMode]

    def __init__(self, device_kind: DeviceKind, measure_kind: MeasureKind, operating_mode: OperatingMode):
        super().__init__(device_kind=device_kind, measure_kind=measure_kind, operating_mode=operating_mode)
