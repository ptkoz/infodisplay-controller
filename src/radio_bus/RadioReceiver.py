import logging
from struct import unpack
from ApplicationContext import ApplicationContext
from command_bus.commands import EvaluateAirConditioning, SaveMeasure, SavePing
from models import AirConditionerPing, SensorMeasure
from radio import InboundMessage, MESSAGE_START_MARKER


class RadioReceiver:
    """
    Class that is responsible for receiving and interpreting data through radio.
    """

    def __init__(self, app: ApplicationContext):
        self.app = app

    def run(self) -> None:
        """
        Run the receiving process. This is meant to be run in a separate thread, as it's blocking
        """
        radio = self.app.radio
        command_bus = self.app.command_queue

        while not self.app.stop_requested:
            radio.serial.timeout = 5
            if radio.serial.read(1) != MESSAGE_START_MARKER:
                # skip anything and wait for message beginning
                continue

            [size] = radio.serial.read(1)
            if size is None:
                logging.warning("Message start received, but then timed out on waiting for message size")
                # timeout on reading the message length
                continue

            msg = InboundMessage.receive_from_radio(self.app.radio, size)
            if msg is None:
                logging.warning("Unable to read message of size %d from radio", size)
                continue

            timestamp = self.app.time_source.now()

            if msg.recipient != 0xA1:
                logging.info('Ignoring message to %#x (with %d bytes)', msg.recipient, msg.length)
                continue

            if msg.kind == AirConditionerPing.MESSAGE_KIND:
                if msg.length != 0:
                    logging.warning("Unexpected %d bytes in %#x message", msg.length, msg.kind)
                command_bus.put_nowait(SavePing(timestamp))
            elif msg.kind in [SensorMeasure.LIVING_ROOM, SensorMeasure.BEDROOM]:
                if msg.length != 12:
                    logging.warning("Ignoring message %#x: expected 12 bytes, got %d", msg.kind, msg.length)
                    continue

                [temperature, humidity, voltage] = unpack("<fff", msg.data)
                command_bus.put_nowait(SaveMeasure(timestamp, msg.kind, temperature, humidity, voltage))
                if msg.kind == SensorMeasure.LIVING_ROOM:
                    command_bus.put_nowait(EvaluateAirConditioning())
            elif msg.kind == SensorMeasure.OUTDOOR:
                if msg.length != 8:
                    logging.warning("Ignoring message %#x: expected 8 bytes, got %d", msg.kind, msg.length)
                    continue

                [temperature, voltage] = unpack("<ff", msg.data)
                command_bus.put_nowait(SaveMeasure(timestamp, msg.kind, temperature, None, voltage))
            else:
                logging.warning('Unrecognized message kind %#x (with %d bytes)', msg.kind, msg.length)
