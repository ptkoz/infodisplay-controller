from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from .AbstractBase import AbstractBase


class NounceRequestResponseLog(AbstractBase):
    """
    Representation of nounce numbers used by each device for both inbound and outbound communication.
    """

    __tablename__ = "nounce_request_response_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner: Mapped[int]
    timestamp: Mapped[datetime]
    responded_inbound_nounce: Mapped[int]
    responded_outbound_nounce: Mapped[int]

    def __init__(self, owner: int, timestamp: datetime, responded_inbound_nounce: int, responded_outbound_nounce: int):
        super().__init__(
            owner=owner,
            timestamp=timestamp,
            responded_inbound_nounce=responded_inbound_nounce,
            responded_outbound_nounce=responded_outbound_nounce
        )
