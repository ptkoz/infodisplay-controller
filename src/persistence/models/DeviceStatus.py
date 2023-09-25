from datetime import datetime
from sqlalchemy import Index
from sqlalchemy.orm import mapped_column, Mapped
from domain_types import DeviceKind, PowerStatus
from .AbstractBase import AbstractBase


class DeviceStatus(AbstractBase):
    """
    Represent a change in device power status
    """
    __tablename__ = "device_status"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kind: Mapped[DeviceKind]
    timestamp: Mapped[datetime]
    status: Mapped[PowerStatus]

    __table_args__ = (
        Index('device_status_by_kind_idx', "kind", "timestamp"),
        Index('device_status_by_kind_status_idx', "kind", "status", "timestamp"),
    )

    def __init__(self, kind: DeviceKind, timestamp: datetime, status: PowerStatus):
        super().__init__(kind=kind, timestamp=timestamp, status=status)
