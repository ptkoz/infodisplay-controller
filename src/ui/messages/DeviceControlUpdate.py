from typing import List
from domain_types import DeviceKind, OperatingMode
from persistence import DeviceControl


class DeviceControlUpdate(dict):
    """
    A message sent when measures that control given device have been changed.
    """

    def __init__(self, device_kind: DeviceKind, device_control: List[DeviceControl]):
        controlled_by: dict = {}

        for mode in OperatingMode:
            controlled_by[mode.value] = []

        for control in device_control:
            controlled_by[control.operating_mode.value].append(control.measure_kind.value)

        super().__init__(
            type="device/updateDeviceControl",
            payload={
                "deviceKind": device_kind.value,
                "controlledBy": controlled_by
            }
        )
