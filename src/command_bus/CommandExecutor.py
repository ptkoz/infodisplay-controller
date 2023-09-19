import logging
import traceback
from datetime import datetime
from queue import Empty, Queue
from threading import Event
from typing import Type
from sqlalchemy.orm import sessionmaker, Session
from radio_bus import Radio
from ui import Publisher
from .commands.AbstractCommand import AbstractCommand
from .ExecutionContext import ExecutionContext


class CommandExecutor:
    """
    Fetches commands from the queue and executes them with given context. Is meant to run in a
    thread.
    """

    def __init__(
        self,
        db_session_factory: sessionmaker[Session],  # pylint: disable=E1136
        radio: Radio,
        command_bus: Queue,
        publisher: Publisher,
        time_source: Type[datetime],
        stop: Event
    ):
        self.db_session_factory = db_session_factory
        self.radio = radio
        self.command_bus = command_bus
        self.publisher = publisher
        self.time_source = time_source
        self.stop = stop

    def run(self) -> None:
        """
        Runs the main loop that waits for command to appear on command queue and executes them.
        """
        execution_context = self.create_execution_context()
        while not self.stop.is_set():
            try:
                command = self.command_bus.get(timeout=5)
                if isinstance(command, AbstractCommand):
                    command.execute(execution_context)
                    self.command_bus.task_done()
            except Empty:
                continue
            except Exception:
                logging.error(traceback.format_exc())

                # Reset context just in case
                execution_context.db_session.close()
                execution_context = self.create_execution_context()

        execution_context.db_session.close()

    def create_execution_context(self) -> ExecutionContext:
        """
        Creates a new instance of execution context
        """
        return ExecutionContext(
            self.db_session_factory(),
            self.radio,
            self.command_bus,
            self.publisher,
            datetime,
        )
