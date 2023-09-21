class AcStatusUpdate(dict):
    """
    A message sent AC status changes
    """

    def __init__(self, is_working: bool):
        super().__init__(
            type="ac/updateStatus",
            payload=is_working
        )
