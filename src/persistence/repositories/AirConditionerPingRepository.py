from datetime import datetime
from typing import Optional
from persistence.models import AirConditionerPing
from ._AbstractRepository import AbstractRepository


class AirConditionerPingRepository(AbstractRepository):
    """
    Repository for air conditioner pings
    """

    def get_last_ping(self) -> Optional[AirConditionerPing]:
        """
        Returns most recently recorded ping
        """
        return (
            self._session
            .query(AirConditionerPing)
            .order_by(AirConditionerPing.timestamp.desc())
            .first()
        )

    def create(self, ping_timestamp: datetime) -> AirConditionerPing:
        """
        Creates and records new ping object with given timestamp
        """
        ping = AirConditionerPing(ping_timestamp)
        self._session.add(ping)
        self._session.commit()
        return ping
