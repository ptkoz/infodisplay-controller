class AwayStatusUpdate(dict):
    """
    A message sent when AC status has changed
    """

    def __init__(self, is_away: bool):
        super().__init__(
            type="device/setAway",
            payload=is_away
        )
