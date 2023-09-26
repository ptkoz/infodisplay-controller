from datetime import datetime
from domain_types import MeasureKind


class HumidityUpdate(dict):
    """
    A message sent when new humidity measure is available.
    """

    def __init__(self, timestamp: datetime, kind: MeasureKind, humidity: float):
        super().__init__(
            type="measure/updateHumidity",
            payload={
                "timestamp": timestamp.isoformat(),
                "kind": kind.value,
                "humidity": humidity,
            }
        )
