class TargetTemperatureUpdate(dict):
    """
    A message sent when target temperature has been updated
    """

    def __init__(self, temperature: float):
        super().__init__(
            type="ac/updateTargetTemperature",
            payload=temperature
        )
