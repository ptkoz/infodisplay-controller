import logging
from datetime import datetime
from queue import Queue
from struct import unpack
from threading import Event
from typing import Type
from secrets import MY_ADDRESS
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
                # skip everything and wait for message beginning
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

            if msg.to_address != MY_ADDRESS:
                logging.info(
                    'Ignoring message from %#x to %#x (with %d bytes)',
                    msg.from_address,
                    msg.to_address,
                    msg.extended_bytes_length
                )
                continue

            if not msg.is_valid(0):
                logging.warning(
                    "Received message %#x from %#x, but it could not be authenticated",
                    msg.command,
                    msg.from_address
                )
                continue

            if msg.from_address in [DeviceKind.HEATING.value, DeviceKind.COOLING.value] and msg.command == 0x01:
                if msg.extended_bytes_length != 1:
                    logging.warning(
                        "Ignoring message %#x from %#x: expected 1 byte, got %d",
                        msg.command,
                        msg.from_address,
                        msg.extended_bytes_length
                    )
                    continue

                from command_bus import SavePing
                self.command_bus.put_nowait(SavePing(DeviceKind(msg.from_address), self.time_source.now()))
            elif msg.from_address in [MeasureKind.LIVING_ROOM.value, MeasureKind.BEDROOM.value] and msg.command == 0x01:
                if msg.extended_bytes_length != 12:
                    logging.warning(
                        "Ignoring message %#x from %#x: expected 12 bytes, got %d",
                        msg.command,
                        msg.from_address,
                        msg.extended_bytes_length
                    )
                    continue

                [temperature, humidity, voltage] = unpack("<fff", msg.extended_bytes)
                measure = SensorMeasure(
                    self.time_source.now(), MeasureKind(msg.from_address), temperature, humidity, voltage
                )

                from command_bus import SaveMeasure
                self.command_bus.put_nowait(SaveMeasure(measure))
                from command_bus import EvaluateMeasure
                self.command_bus.put_nowait(EvaluateMeasure(measure))
            elif msg.from_address == MeasureKind.OUTDOOR.value and msg.command == 0x01:
                if msg.extended_bytes_length != 8:
                    logging.warning(
                        "Ignoring message %#x from %#x: expected 8 bytes, got %d",
                        msg.command,
                        msg.from_address,
                        msg.extended_bytes_length
                    )
                    continue

                [temperature, voltage] = unpack("<ff", msg.extended_bytes)
                measure = SensorMeasure(self.time_source.now(), MeasureKind(msg.command), temperature, None, voltage)
                from command_bus import SaveMeasure
                self.command_bus.put_nowait(SaveMeasure(measure))
            else:
                logging.warning(
                    'Unrecognized message %#x from %#x (with %d bytes)',
                    msg.command,
                    msg.from_address,
                    msg.extended_bytes_length
                )
