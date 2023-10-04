import logging
from persistence import DeviceStatusRepository
from domain_types import DeviceKind, PowerStatus
from ui import DeviceStatusUpdate
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class RecordDeviceStatus(AbstractCommand):
    """
    Command that ensures device status is as received from the device itself
    """

    def __init__(self, kind: DeviceKind, is_working: bool):
        self.kind = kind
        self.is_working = is_working

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        status_repository = DeviceStatusRepository(context.db_session)
        current_status = status_repository.get_current_status(self.kind)
        if self.is_working and current_status == PowerStatus.TURNED_OFF:
            logging.info("Device %s was expected to be off, but it is on. Overthrowing status.", self.kind.name)
            status_repository.set_current_status(self.kind, PowerStatus.TURNED_ON, context.time_source.now())
            context.publisher.publish(DeviceStatusUpdate(self.kind, True))

        if not self.is_working and current_status == PowerStatus.TURNED_ON:
            logging.info("Device %s was expected to be on, but it is off. Overthrowing status.", self.kind.name)
            status_repository.set_current_status(self.kind, PowerStatus.TURNED_OFF, context.time_source.now())
            context.publisher.publish(DeviceStatusUpdate(self.kind, False))
