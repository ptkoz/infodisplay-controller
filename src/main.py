import logging
import signal
import threading
from datetime import datetime
from queue import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from command_bus import CommandExecutor
from persistence import AbstractBase
from radio_bus import Radio, RadioReceiver
from ui import Controller

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

stop = threading.Event()
command_bus = Queue()
radio = Radio("/dev/ttyS0", 17)
db_engine = create_engine("sqlite:////var/lib/infodisplay/database.db")
db_session_factory = sessionmaker(db_engine)

radio.setup_device()
AbstractBase.metadata.create_all(db_engine)

receiver = RadioReceiver(radio, command_bus, datetime, stop)
executor = CommandExecutor(db_session_factory, radio, command_bus, datetime, stop)
controller = Controller(8001, stop)

receiving_thread = threading.Thread(target=receiver.run)
executor_thread = threading.Thread(target=executor.run)
controller_thread = threading.Thread(target=controller.run)

receiving_thread.start()
executor_thread.start()
controller_thread.start()


# pylint: disable=W0613
def sig_handler(signum, frame):
    """
    Catches interrupt signals and kicks off graceful shutdown of an application
    """
    logging.info('Received signal %s, stopping gracefully', signal.Signals(signum).name)
    stop.set()


signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

receiving_thread.join()
executor_thread.join()
controller_thread.join()
