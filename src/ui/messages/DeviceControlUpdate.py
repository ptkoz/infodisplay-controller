from typing import List

from domain_types import DeviceKind, MeasureKind


class DeviceControlUpdate(dict):
    """
    A message sent when measures that control given device have been changed.
    """

    def __init__(self, device_kind: DeviceKind, measure_kinds: List[MeasureKind]):
        super().__init__(
            type="device/updateDeviceControl",
            payload={
                "deviceKind": device_kind,
                "controlledBy": measure_kinds
            }
        )
