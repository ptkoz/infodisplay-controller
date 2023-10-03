import logging
import traceback
from datetime import datetime
from queue import Empty, Queue
from struct import unpack
from threading import Event
from typing import Optional, Type
from secrets import MY_ADDRESS
from sqlalchemy.orm import Session, sessionmaker
from domain_types import DeviceKind, MeasureKind
from persistence import NounceRepository, SensorMeasure
from .radio.InboundMessage import InboundMessage
from .radio.OutboundMessage import OutboundMessage
from .radio.Radio import Radio
from .radio.MessageStartMarker import MESSAGE_START_MARKER


class RadioController:
    """
    Class that is responsible for receiving and interpreting data through radio.
    """

    def __init__(
        self,
        radio: Radio,
        outbound_bus: Queue,
        command_bus: Queue,
        time_source: Type[datetime],
        stop: Event,
        db_session_factory: sessionmaker[Session]  # pylint: disable=E1136
    ):
        self.radio = radio
        self.outbound_bus = outbound_bus
        self.command_bus = command_bus
        self.time_source = time_source
        self.stop = stop
        self.db_session_factory = db_session_factory

    def run(self) -> None:
        """
        Run the receiving process. This is meant to be run in a separate thread, as it's blocking
        """
        while not self.stop.is_set():
            try:
                inbound = self.get_validated_message()
                if inbound is not None:
                    self.handle_nounce_request(inbound)
                    self.handle_ping(inbound)
                    self.handle_indoor_measure(inbound)
                    self.handle_outdoor_measure(inbound)

                outbound = self.outbound_bus.get(timeout=3)
                if isinstance(outbound, OutboundMessage):
                    self.radio.send(outbound)
                    self.outbound_bus.task_done()
            except Empty:
                continue
            except Exception:
                logging.error(traceback.format_exc())

    def get_validated_message(self) -> Optional[InboundMessage]:
        """
        Attempts to receive an inbound message from radio returns it only if it's valid
        """
        msg = self.get_next_message()

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

        if msg.command == 0x00 and msg.is_valid(-1):
            # This message is nounce request, don't validate against repetition
            return msg

        with self.db_session_factory() as db_session:
            nounce_repository = NounceRepository(db_session)
            if not msg.is_valid(nounce_repository.get_last_inbound_nounce(msg.from_address)):
                logging.warning(
                    "Received message %#x from %#x, but it could not be authenticated",
                    msg.command,
                    msg.from_address
                )
                return None

            nounce_repository.register_inbound_nounce(msg.from_address, msg.nounce)
            db_session.commit()
        return msg

    def get_next_message(self) -> Optional[InboundMessage]:
        """
        Attempts to receive an inbound message from radio
        """
        self.radio.serial.timeout = 1
        while True:
            marker = self.radio.serial.read(1)

            if len(marker) == 0:
                # timeout waiting for marker
                return None

            if marker == MESSAGE_START_MARKER:
                # start marker received, continue
                break

        self.radio.serial.timeout = 5
        size = self.radio.serial.read(1)
        if len(size) != 1:
            logging.warning("Message start received, but then timed out on waiting for message size")
            # timeout on reading the message length
            return None

        size = int.from_bytes(size, byteorder="little", signed=False)
        msg = InboundMessage.receive_from_radio(self.radio, size)
        if msg is None:
            logging.warning("Unable to read message of size %d from radio", size)
            return None

        return msg

    def handle_nounce_request(self, msg: InboundMessage) -> None:
        """
        Handle message, if it is a nounce request from device
        """
        if msg.command != 0x00:
            return

        from command_bus import RespondNounceRequest
        self.command_bus.put_nowait(RespondNounceRequest(msg.from_address))

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
        if msg.from_address not in [MeasureKind.LIVING_ROOM.value, MeasureKind.BEDROOM.value] or msg.command != 0x01:
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
            self.time_source.now(), MeasureKind(msg.from_address), temperature, None, voltage
        )

        from command_bus import SaveMeasure
        self.command_bus.put_nowait(SaveMeasure(measure))
