class AcManagementUpdate(dict):
    """
    A message sent when ac management status has changed
    """

    def __init__(self, is_managed: bool):
        super().__init__(
            type="ac/updateManagementStatus",
            payload=is_managed
        )
