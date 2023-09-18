from datetime import datetime
from enum import Enum
from sqlalchemy.orm import mapped_column, Mapped
from .AbstractBase import AbstractBase


class AirConditionerStatus(Enum):
    """
    Available air conditioner statuses
    """
    TURNED_ON = 1
    TURNED_OFF = 0
    UNAVAILABLE = -1


class AirConditionerStatusLog(AbstractBase):
    """
    Represent the change of air conditioner status
    """
    __tablename__ = "air_conditioner_status_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(index=True)
    status: Mapped[AirConditionerStatus] = mapped_column(index=True)

    def __init__(self, timestamp: datetime, status: AirConditionerStatus):
        super().__init__(timestamp=timestamp, status=status)
