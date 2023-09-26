from datetime import datetime
from domain_types import DeviceKind


class DevicePingReceived(dict):
    """
    A message sent when ac sends us a ping
    """

    def __init__(self, device_kind: DeviceKind, timestamp: datetime):
        super().__init__(
            type="device/ping",
            payload={
                "kind": device_kind.value,
                "timestamp": timestamp.isoformat(),
            }
        )
