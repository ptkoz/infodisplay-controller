from persistence import ThresholdTemperature


class ThresholdTemperatureUpdate(dict):
    """
    A message sent when threshold temperature has been updated for given device kind and mode
    """

    def __init__(self, threshold_temperature: ThresholdTemperature):
        super().__init__(
            type="device/updateThresholdTemperature",
            payload={
                "kind": threshold_temperature.device_kind.value,
                "mode": threshold_temperature.operating_mode.value,
                "temperature": threshold_temperature.temperature
            }
        )
