from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from .AbstractBase import AbstractBase


class AirConditionerPing(AbstractBase):
    """
    A class representing recorded ping form air conditioner
    """

    # Message kind for ping received over the radio
    MESSAGE_KIND = 0x90

    __tablename__ = "air_conditioner_ping"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(index=True)

    def __init__(self, timestamp: datetime):
        super().__init__(timestamp=timestamp)
