from datetime import datetime


class AcPing(dict):
    """
    A message sent when ac sends us a ping
    """

    def __init__(self, timestamp: datetime):
        super().__init__(
            type="ac/ping",
            payload=timestamp.isoformat()
        )
