from typing_extensions import Protocol


class Publisher(Protocol):
    """
    Interface for publishing messages to ui clients
    """

    def publish(self, message: dict) -> None:
        """
        Publishes message to all connected ui clients
        """
        raise NotImplementedError
