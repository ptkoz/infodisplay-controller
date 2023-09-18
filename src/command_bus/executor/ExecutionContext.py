from datetime import datetime
from queue import Queue
from typing import Type
from sqlalchemy.orm import Session
from radio_bus.radio import Radio


class ExecutionContext:
    """
    Class providing context to executed commands
    """

    def __init__(self, db_session: Session, time_source: Type[datetime], command_queue: Queue, radio: Radio):
        self.persistence = db_session
        self.time_source = time_source
        self.command_queue = command_queue
        self.radio = radio
