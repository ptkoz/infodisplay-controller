class AwayStatusUpdate(dict):
    """
    A message sent when AC status has changed
    """

    def __init__(self, is_away: bool):
        super().__init__(
            type="device/updateAwayStatus",
            payload=is_away
        )
