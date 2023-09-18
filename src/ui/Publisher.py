from typing import Protocol

from ui.events import AbstractEvent


class Publisher(Protocol):
    """
    Interface for publishing events to the UI
    """
    def publish(self, event: AbstractEvent) -> None:
        """

        """
        raise NotImplementedError
