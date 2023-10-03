from datetime import datetime
from typing import Optional
from persistence.models import DevicePing
from domain_types import DeviceKind
from ._AbstractRepository import AbstractRepository


class DevicePingRepository(AbstractRepository):
    """
    Repository for air conditioner pings
    """

    def get_last_ping(self, kind: DeviceKind) -> Optional[DevicePing]:
        """
        Returns most recently recorded ping for given device kind
        """
        return (
            self._session
            .query(DevicePing)
            .filter(DevicePing.kind == kind)
            .order_by(DevicePing.timestamp.desc())
            .first()
        )

    def create(self, kind: DeviceKind, timestamp: datetime) -> DevicePing:
        """
        Creates and records new ping object with given timestamp and device kind
        """
        ping = DevicePing(kind, timestamp)
        self._session.add(ping)
        return ping
