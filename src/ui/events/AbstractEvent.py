import json


class AbstractEvent:
    """
    Base class for UI events
    """

    def to_json(self) -> str:
        """
        Encodes object to json string
        """
        return json.dumps(self, default=lambda o: o.__dict__)
