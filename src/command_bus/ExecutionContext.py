from datetime import datetime
from queue import Queue
from typing import Type
from sqlalchemy.orm import Session
from ui.UiPublisher import UiPublisher


class ExecutionContext:
    """
    Class providing context to executed commands
    """

    def __init__(
        self,
        db_session: Session,
        outbound_bus: Queue,
        command_bus: Queue,
        publisher: UiPublisher,
        time_source: Type[datetime]
    ):
        self.db_session = db_session
        self.outbound_bus = outbound_bus
        self.command_queue = command_bus
        self.publisher = publisher
        self.time_source = time_source
