from persistence import TargetTemperature


class TargetTemperatureUpdate(dict):
    """
    A message sent when target temperature has been updated for given device kind and mode
    """

    def __init__(self, target_temperature: TargetTemperature):
        super().__init__(
            type="device/updateTargetTemperature",
            payload={
                "kind": target_temperature.device_kind.value,
                "mode": target_temperature.operating_mode.value,
                "temperature": target_temperature.temperature
            }
        )
