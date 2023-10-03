import logging
import traceback
from datetime import datetime
from queue import Empty, Queue
from threading import Event
from typing import Type
from sqlalchemy.orm import sessionmaker, Session
from ui.UiPublisher import UiPublisher
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
        outbound_bus: Queue,
        command_bus: Queue,
        publisher: UiPublisher,
        time_source: Type[datetime],
        stop: Event
    ):
        self.db_session_factory = db_session_factory
        self.outbound_bus = outbound_bus
        self.command_bus = command_bus
        self.publisher = publisher
        self.time_source = time_source
        self.stop = stop

    def run(self) -> None:
        """
        Runs the main loop that waits for command to appear on command queue and executes them.
        """
        while not self.stop.is_set():
            try:
                command = self.command_bus.get(timeout=5)
                if isinstance(command, AbstractCommand):
                    with self.db_session_factory() as db_session:
                        command.execute(
                            ExecutionContext(
                                db_session,
                                self.outbound_bus,
                                self.command_bus,
                                self.publisher,
                                datetime,
                            )
                        )
                        db_session.commit()
                    self.command_bus.task_done()
            except Empty:
                continue
            except Exception:
                logging.error(traceback.format_exc())
