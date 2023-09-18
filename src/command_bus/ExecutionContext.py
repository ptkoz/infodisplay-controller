from datetime import datetime
from queue import Queue
from typing import Type
from sqlalchemy.orm import Session
from radio_bus.radio import Radio


class ExecutionContext:
    """
    Class providing context to executed commands
    """

    def __init__(self, db_session: Session, radio: Radio, command_bus: Queue, time_source: Type[datetime]):
        self.db_session = db_session
        self.radio = radio
        self.command_queue = command_bus
        self.time_source = time_source
