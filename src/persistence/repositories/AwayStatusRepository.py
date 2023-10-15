from datetime import datetime
from persistence.models import AwayStatus
from domain_types import PowerStatus
from ._AbstractRepository import AbstractRepository


class AwayStatusRepository(AbstractRepository):
    """
    Repository for away status changes
    """

    def set_away_status(self, timestamp: datetime, status: PowerStatus):
        """
        Record the current away status for given timestamp
        """
        self._session.add(AwayStatus(timestamp, status))

    def is_away(self) -> bool:
        """
        Checks whether away status is currently set to ON
        """
        last_status = (
            self._session
            .query(AwayStatus)
            .order_by(AwayStatus.timestamp.desc())
            .first()
        )

        if last_status is None:
            return False

        return last_status.status == PowerStatus.TURNED_ON
