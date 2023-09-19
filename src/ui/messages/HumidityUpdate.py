from datetime import datetime


class HumidityUpdate(dict):
    """
    A message sent when a new measure is available.
    """

    def __init__(self, timestamp: datetime, kind: int, humidity: float):
        super().__init__(
            type="measures/updateHumidity",
            payload={
                'timestamp': timestamp.isoformat(),
                'kind': kind,
                'humidity': humidity,
            }
        )
