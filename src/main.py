import logging
import signal
import threading
from ApplicationContext import ApplicationContext
from command_bus import CommandExecutor
from radio_bus import RadioReceiver

app = ApplicationContext()

receiver = RadioReceiver(app)
executor = CommandExecutor(app)

receiving_thread = threading.Thread(target=receiver.run)
executor_thread = threading.Thread(target=executor.run)

receiving_thread.start()
executor_thread.start()

# pylint: disable=W0613
def sig_handler(signum, frame):
    """
    Catches interrupt signals and kicks off graceful shutdown of an application
    """
    logging.info('Received signal %s, stopping gracefully', signal.Signals(signum).name)
    app.stop_requested = True


signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

receiving_thread.join()
executor_thread.join()
