from datetime import datetime
from typing import Optional
from persistence.models import DeviceStatus
from domain_types import DeviceKind, PowerStatus
from ._AbstractRepository import AbstractRepository


class DeviceStatusRepository(AbstractRepository):
    """
    Repository for device status changes
    """

    def set_current_status(self, kind: DeviceKind, status: PowerStatus, timestamp: datetime):
        """
        Logs device status
        """
        self._session.add(DeviceStatus(kind, timestamp, status))
        self._session.commit()

    def get_current_status(self, kind: DeviceKind) -> PowerStatus:
        """
        Returns the current status of given device kind (most recently logged status)
        """
        last_status = (
            self._session
            .query(DeviceStatus)
            .filter(DeviceStatus.kind == kind)
            .order_by(DeviceStatus.timestamp.desc())
            .first()
        )

        if last_status is None:
            return PowerStatus.TURNED_OFF

        return last_status.status

    def get_last_turn_on(self, kind: DeviceKind) -> Optional[DeviceStatus]:
        """
        Returns the status log for when the AirConditioner was most recently turned on
        """
        return (
            self._session
            .query(DeviceStatus)
            .filter(DeviceStatus.kind == kind)
            .filter(DeviceStatus.status == PowerStatus.TURNED_ON)
            .order_by(DeviceStatus.timestamp.desc())
            .first())

    def get_last_turn_off(self, kind: DeviceKind) -> Optional[DeviceStatus]:
        """
        Returns the status log for when the AirConditioner was most recently turned off
        """
        return (
            self._session
            .query(DeviceStatus)
            .filter(DeviceStatus.kind == kind)
            .filter(DeviceStatus.status == PowerStatus.TURNED_OFF)
            .order_by(DeviceStatus.timestamp.desc())
            .first())
