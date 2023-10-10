import logging
from logging.handlers import WatchedFileHandler
import signal
import threading
from datetime import datetime
from queue import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from command_bus import CommandExecutor
from persistence import AbstractBase
from radio_bus import Radio, RadioController
from ui import UiController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[WatchedFileHandler("/var/log/infodisplay.log")]
)
logging.getLogger('websockets.server').setLevel(logging.WARNING)
logging.getLogger('websockets.protocol').setLevel(logging.WARNING)

stop = threading.Event()
command_bus: Queue = Queue()
outbound_bus: Queue = Queue()
radio = Radio("/dev/ttyS0", 17)
db_engine = create_engine("sqlite:////var/lib/infodisplay/database.db")
db_session_factory = sessionmaker(db_engine, expire_on_commit=False)

radio.setup_device()
AbstractBase.metadata.create_all(db_engine)

ui_controller = UiController(8010, command_bus, stop)
radio_controller = RadioController(radio, outbound_bus, command_bus, datetime, stop, db_session_factory)
executor = CommandExecutor(db_session_factory, outbound_bus, command_bus, ui_controller, datetime, stop)

radio_thread = threading.Thread(target=radio_controller.run)
command_thread = threading.Thread(target=executor.run)
ui_thread = threading.Thread(target=ui_controller.run)

radio_thread.start()
command_thread.start()
ui_thread.start()


# pylint: disable=W0613
def sig_handler(signum, frame):
    """
    Catches interrupt signals and kicks off graceful shutdown of an application
    """
    logging.info('Received signal %s, stopping gracefully', signal.Signals(signum).name)
    stop.set()


signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

radio_thread.join()
command_thread.join()
ui_thread.join()
