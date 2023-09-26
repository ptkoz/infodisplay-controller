from domain_types import DeviceKind


class DeviceStatusUpdate(dict):
    """
    A message sent when AC status has changed
    """

    def __init__(self, kind: DeviceKind, is_working: bool):
        super().__init__(
            type="device/updateStatus",
            payload={
                "kind": kind.value,
                "isWorking": is_working
            }
        )
