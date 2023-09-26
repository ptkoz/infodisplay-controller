import logging
from datetime import datetime
from queue import Queue
from struct import unpack
from threading import Event
from typing import Type
from domain_types import DeviceKind, MeasureKind
from persistence import SensorMeasure
from .radio.InboundMessage import InboundMessage
from .radio.Radio import Radio
from .radio.MessageStartMarker import MESSAGE_START_MARKER


class RadioReceiver:
    """
    Class that is responsible for receiving and interpreting data through radio.
    """

    def __init__(self, radio: Radio, command_bus: Queue, time_source: Type[datetime], stop: Event):
        self.radio = radio
        self.command_bus = command_bus
        self.time_source = time_source
        self.stop = stop

    def run(self) -> None:
        """
        Run the receiving process. This is meant to be run in a separate thread, as it's blocking
        """
        while not self.stop.is_set():
            self.radio.serial.timeout = 5
            if self.radio.serial.read(1) != MESSAGE_START_MARKER:
                # skip anything and wait for message beginning
                continue

            [size] = self.radio.serial.read(1)
            if size is None:
                logging.warning("Message start received, but then timed out on waiting for message size")
                # timeout on reading the message length
                continue

            msg = InboundMessage.receive_from_radio(self.radio, size)
            if msg is None:
                logging.warning("Unable to read message of size %d from radio", size)
                continue

            timestamp = self.time_source.now()

            if msg.recipient != 0xA1:
                logging.info('Ignoring message to %#x (with %d bytes)', msg.recipient, msg.length)
                continue

            if msg.kind in [DeviceKind.HEATING.value, DeviceKind.COOLING.value]:
                if msg.length != 0:
                    logging.warning("Unexpected %d bytes in %#x message", msg.length, msg.kind)

                from command_bus import SavePing
                self.command_bus.put_nowait(SavePing(DeviceKind(msg.kind), timestamp))
            elif msg.kind in [MeasureKind.LIVING_ROOM.value, MeasureKind.BEDROOM.value]:
                if msg.length != 12:
                    logging.warning("Ignoring message %#x: expected 12 bytes, got %d", msg.kind, msg.length)
                    continue

                [temperature, humidity, voltage] = unpack("<fff", msg.data)
                measure = SensorMeasure(timestamp, MeasureKind(msg.kind), temperature, humidity, voltage)

                from command_bus import SaveMeasure
                self.command_bus.put_nowait(SaveMeasure(measure))
                from command_bus import EvaluateMeasure
                self.command_bus.put_nowait(EvaluateMeasure(measure))
            elif msg.kind == MeasureKind.OUTDOOR.value:
                if msg.length != 8:
                    logging.warning("Ignoring message %#x: expected 8 bytes, got %d", msg.kind, msg.length)
                    continue

                [temperature, voltage] = unpack("<ff", msg.data)
                measure = SensorMeasure(timestamp, MeasureKind(msg.kind), temperature, None, voltage)
                from command_bus import SaveMeasure
                self.command_bus.put_nowait(SaveMeasure(measure))
            else:
                logging.warning('Unrecognized message kind %#x (with %d bytes)', msg.kind, msg.length)
