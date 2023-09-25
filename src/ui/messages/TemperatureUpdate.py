from datetime import datetime
from domain_types import MeasureKind


class TemperatureUpdate(dict):
    """
    A message sent when new temperature measure is available.
    """

    def __init__(self, timestamp: datetime, kind: MeasureKind, temperature: float):
        super().__init__(
            type="measures/updateTemperature",
            payload={
                "timestamp": timestamp.isoformat(),
                "kind": kind,
                "temperature": temperature,
            }
        )
