from datetime import datetime
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from domain_types import DeviceKind
from .AbstractBase import AbstractBase


class DevicePing(AbstractBase):
    """
    A class representing a ping from a remote device
    """
    __tablename__ = "device_ping"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[DeviceKind]
    timestamp: Mapped[datetime]

    __table_args__ = (
        Index('device_ping_by_kind_idx', "kind", "timestamp"),
    )

    def __init__(self, kind: DeviceKind, timestamp: datetime):
        super().__init__(kind=kind, timestamp=timestamp)
