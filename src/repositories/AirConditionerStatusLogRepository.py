from datetime import datetime
from typing import Optional
from models import AirConditionerStatusLog, AirConditionerStatus
from repositories._AbstractRepository import AbstractRepository


class AirConditionerStatusLogRepository(AbstractRepository):
    """
    Repository for air conditioner status changes
    """

    def set_current_status(self, status: AirConditionerStatus, timestamp: datetime):
        """
        Logs air conditioner status
        """
        self._session.add(AirConditionerStatusLog(timestamp, status))
        self._session.commit()

    def get_current_status(self) -> AirConditionerStatus:
        """
        Returns the status log for when the AirConditioner was most recently turned on
        """
        last_status_log = (
            self._session
            .query(AirConditionerStatusLog)
            .order_by(AirConditionerStatusLog.timestamp.desc())
            .first()
        )

        if last_status_log is None:
            return AirConditionerStatus.TURNED_OFF

        return last_status_log.status

    def get_last_turn_on(self) -> Optional[AirConditionerStatusLog]:
        """
        Returns the status log for when the AirConditioner was most recently turned on
        """
        return (
            self._session
            .query(AirConditionerStatusLog)
            .filter(AirConditionerStatusLog.status == AirConditionerStatus.TURNED_ON)
            .order_by(AirConditionerStatusLog.timestamp.desc())
            .first())

    def get_last_turn_off(self) -> Optional[AirConditionerStatusLog]:
        """
        Returns the status log for when the AirConditioner was most recently turned off
        """
        return (
            self._session
            .query(AirConditionerStatusLog)
            .filter(AirConditionerStatusLog.status == AirConditionerStatus.TURNED_OFF)
            .order_by(AirConditionerStatusLog.timestamp.desc())
            .first())
