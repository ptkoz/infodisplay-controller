class AcStatusUpdate(dict):
    """
    A message sent when AC status has changed
    """

    def __init__(self, is_working: bool):
        super().__init__(
            type="ac/updateStatus",
            payload=is_working
        )
