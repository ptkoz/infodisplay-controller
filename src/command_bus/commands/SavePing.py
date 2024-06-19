import logging
from datetime import datetime

from persistence import DevicePingRepository
from domain_types import DeviceKind
from ui import DevicePingReceived
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
        logging.debug("Saving ping from %s", self.kind.name)

        ping_repository = DevicePingRepository(context.db_session)
        ping_repository.create(self.kind, self.timestamp)
        context.publisher.publish(DevicePingReceived(self.kind, self.timestamp))
