from datetime import datetime
from sqlalchemy import Index
from sqlalchemy.orm import mapped_column, Mapped
from domain_types import PowerStatus
from .AbstractBase import AbstractBase


class AwayStatus(AbstractBase):
    """
    Represent in away controlling mode. In away mode all device controlling is disabled, we just ensure
    the temperature does not drop below 14C (anti-freeze protection).
    """
    __tablename__ = "away_status"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime]
    status: Mapped[PowerStatus]

    __table_args__ = (
        Index('away_status_by_timestamp_idx', "timestamp"),
    )

    def __init__(self, timestamp: datetime, status: PowerStatus):
        super().__init__(timestamp=timestamp, status=status)
