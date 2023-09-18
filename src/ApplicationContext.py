from datetime import datetime
import logging
from queue import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from persistence import AbstractBase
from radio_bus.radio import Radio


class ApplicationContext:
    """
    Provides and describes the context of the application. Kind of global application state.
    """
    def __init__(self):
        self.__persistence_engine = create_engine("sqlite:////var/lib/infodisplay/database.db")
        self.persistence_session_factory = sessionmaker(self.__persistence_engine)
        self.time_source = datetime
        self.radio = Radio("/dev/ttyS0", 17)
        self.command_queue = Queue()
        self.stop_requested = False

        # Warning, side effects
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        AbstractBase.metadata.create_all(self.__persistence_engine)
        self.radio.setup_device()
