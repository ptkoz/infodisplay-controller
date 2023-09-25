from domain_types import DeviceKind, OperatingMode


class TargetTemperatureUpdate(dict):
    """
    A message sent when target temperature has been updated for given device kind and mode
    """

    def __init__(self, device_kind: DeviceKind, mode: OperatingMode, temperature: float):
        super().__init__(
            type="device/updateTargetTemperature",
            payload={
                "kind": device_kind,
                "mode": mode,
                "temperature": temperature
            }
        )
