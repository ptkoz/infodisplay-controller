from datetime import datetime
from persistence.models import NounceRequestResponseLog
from ._AbstractRepository import AbstractRepository


class NounceRequestResponseRepository(AbstractRepository):
    """
    Repository for persisting the responses we send for nounce requests
    """

    def register(self, owner: int, timestamp: datetime, inbound_nounce: int, outbound_nounce: int):
        """
        Creates a new nounce request response record
        """
        self._session.add(
            NounceRequestResponseLog(owner, timestamp, inbound_nounce, outbound_nounce)
        )
