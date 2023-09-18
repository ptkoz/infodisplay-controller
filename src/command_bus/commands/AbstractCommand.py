from abc import ABC, abstractmethod
from command_bus.executor.ExecutionContext import ExecutionContext


class AbstractCommand(ABC):
    """
    Defines interface for commands that can be handled by CommandExecutor
    """
    @abstractmethod
    def execute(self, context: ExecutionContext) -> None:
        """
        Executes the command
        """
