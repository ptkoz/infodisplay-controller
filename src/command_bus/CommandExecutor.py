import logging
import traceback
from datetime import datetime
from queue import Empty
from ApplicationContext import ApplicationContext
from .ExecutionContext import ExecutionContext
from ._AbstractCommand import AbstractCommand


class CommandExecutor:
    """
    Fetches commands from the queue and executes them with given context. Is meant to run in a
    thread.
    """

    def __init__(self, app: ApplicationContext):
        self.app = app

    def run(self) -> None:
        """
        Runs the main loop that waits for command to appear on command queue and executes them.
        """
        execution_context = self.create_execution_context()
        while not self.app.stop_requested:
            try:
                command = self.app.command_queue.get(timeout=5)
                if isinstance(command, AbstractCommand):
                    command.execute(execution_context)
                    self.app.command_queue.task_done()
            except Empty:
                continue
            except Exception:
                logging.error(traceback.format_exc())

                # Reset context just in case
                execution_context.persistence.close()
                execution_context = self.create_execution_context()

        execution_context.persistence.close()

    def create_execution_context(self) -> ExecutionContext:
        """
        Creates a new instance of execution context
        """
        return ExecutionContext(
            self.app.persistence_session_factory(),
            datetime,
            self.app.command_queue,
            self.app.radio
        )
