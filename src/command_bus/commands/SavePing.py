import logging
from datetime import datetime
from devices import get_device_for_kind
from persistence import DevicePingRepository, DeviceStatusRepository
from domain_types import DeviceKind
from ui import DevicePingReceived
from .EvaluateDevice import EvaluateDevice
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class SavePing(AbstractCommand):
    """
    Command that saves received device ping in the persistence layer and publishes it to the UI
    """

    def __init__(self, kind: DeviceKind, timestamp: datetime):
        self.kind = kind
        self.timestamp = timestamp

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        logging.debug("Saving ping")

        ping_repository = DevicePingRepository(context.db_session)
        device = get_device_for_kind(
            self.kind,
            ping_repository,
            DeviceStatusRepository(context.db_session),
            context.time_source,
            context.publisher,
            context.radio
        )

        was_previously_online = device.is_available()

        ping_repository.create(self.kind, self.timestamp)
        context.publisher.publish(DevicePingReceived(self.kind, self.timestamp))

        if not was_previously_online:
            # Device came back online after period of inactivity. Assume it was off evaluate immediately.
            # Hence, that if assume_off_status recorded status as off, the evaluation won't work due to grace period
            device.assume_off_status()
            context.command_queue.put_nowait(EvaluateDevice(self.kind))
