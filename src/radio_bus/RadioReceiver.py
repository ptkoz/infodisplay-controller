import logging
from datetime import datetime
from queue import Queue
from struct import unpack
from threading import Event
from typing import Optional, Type
from secrets import MY_ADDRESS
from sqlalchemy.orm import Session, sessionmaker
from domain_types import DeviceKind, MeasureKind
from persistence import NounceRepository, SensorMeasure
from .radio.InboundMessage import InboundMessage
from .radio.Radio import Radio
from .radio.MessageStartMarker import MESSAGE_START_MARKER


class RadioReceiver:
    """
    Class that is responsible for receiving and interpreting data through radio.
    """

    def __init__(
        self,
        radio: Radio,
        command_bus: Queue,
        time_source: Type[datetime],
        stop: Event,
        db_session_factory: sessionmaker[Session]  # pylint: disable=E1136
    ):
        self.radio = radio
        self.command_bus = command_bus
        self.time_source = time_source
        self.stop = stop
        self.db_session_factory = db_session_factory

    def run(self) -> None:
        """
        Run the receiving process. This is meant to be run in a separate thread, as it's blocking
        """
        while not self.stop.is_set():
            msg = self.get_validated_message()

            if msg is not None:
                self.handle_ping(msg)
                self.handle_indoor_measure(msg)
                self.handle_outdoor_measure(msg)

    def get_validated_message(self) -> Optional[InboundMessage]:
        """
        Attempts to receive an inbound message from radio returns it only if it's valid
        """
        msg = self.get_message()

        if msg is None:
            return None

        if msg.to_address != MY_ADDRESS:
            logging.info(
                'Ignoring message from %#x to %#x (with %d bytes)',
                msg.from_address,
                msg.to_address,
                msg.extended_bytes_length
            )
            return None

        nounce_repository = NounceRepository(self.db_session_factory())
        if not msg.is_valid(nounce_repository.get_last_inbound_nounce(msg.from_address)):
            logging.warning(
                "Received message %#x from %#x, but it could not be authenticated",
                msg.command,
                msg.from_address
            )
            return None

        nounce_repository.register_inbound_nounce(msg.from_address, msg.nounce)
        return msg

    def get_message(self) -> Optional[InboundMessage]:
        """
        Attempts to receive an inbound message from radio
        """
        self.radio.serial.timeout = 5
        if self.radio.serial.read(1) != MESSAGE_START_MARKER:
            # skip everything and wait for message beginning
            return None

        [size] = self.radio.serial.read(1)
        if size is None:
            logging.warning("Message start received, but then timed out on waiting for message size")
            # timeout on reading the message length
            return None

        msg = InboundMessage.receive_from_radio(self.radio, size)
        if msg is None:
            logging.warning("Unable to read message of size %d from radio", size)
            return None

        return msg

    def handle_ping(self, msg: InboundMessage) -> None:
        """
        Handle message, if it is a ping message from device
        """
        if msg.from_address not in [DeviceKind.HEATING.value, DeviceKind.COOLING.value] or msg.command != 0x01:
            return

        if msg.extended_bytes_length != 1:
            logging.warning(
                "Ignoring message %#x from %#x: expected 1 byte, got %d",
                msg.command,
                msg.from_address,
                msg.extended_bytes_length
            )
            return

        device_kind = DeviceKind(msg.from_address)
        [is_working] = unpack('?', msg.extended_bytes)
        from command_bus import RecordDeviceStatus
        self.command_bus.put_nowait(RecordDeviceStatus(device_kind, is_working))

        from command_bus import SavePing
        self.command_bus.put_nowait(SavePing(device_kind, self.time_source.now()))

    def handle_indoor_measure(self, msg: InboundMessage) -> None:
        """
        Handle message, if it is indoor measure
        """
        if not msg.from_address in [MeasureKind.LIVING_ROOM.value, MeasureKind.BEDROOM.value] or msg.command != 0x01:
            return

        if msg.extended_bytes_length != 12:
            logging.warning(
                "Ignoring message %#x from %#x: expected 12 bytes, got %d",
                msg.command,
                msg.from_address,
                msg.extended_bytes_length
            )
            return

        [temperature, humidity, voltage] = unpack("<fff", msg.extended_bytes)
        measure = SensorMeasure(
            self.time_source.now(), MeasureKind(msg.from_address), temperature, humidity, voltage
        )

        from command_bus import SaveMeasure
        self.command_bus.put_nowait(SaveMeasure(measure))

        from command_bus import EvaluateMeasure
        self.command_bus.put_nowait(EvaluateMeasure(measure))

    def handle_outdoor_measure(self, msg: InboundMessage) -> None:
        """
        Handle message, if it is outdoor measure
        """
        if msg.from_address != MeasureKind.OUTDOOR.value or msg.command != 0x01:
            return

        if msg.extended_bytes_length != 8:
            logging.warning(
                "Ignoring message %#x from %#x: expected 8 bytes, got %d",
                msg.command,
                msg.from_address,
                msg.extended_bytes_length
            )
            return

        [temperature, voltage] = unpack("<ff", msg.extended_bytes)
        measure = SensorMeasure(
            self.time_source.now(), MeasureKind(msg.command), temperature, None, voltage
        )

        from command_bus import SaveMeasure
        self.command_bus.put_nowait(SaveMeasure(measure))
