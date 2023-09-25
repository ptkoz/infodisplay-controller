from persistence import SensorMeasure, DeviceControlRepository
from .AbstractCommand import AbstractCommand
from .EvaluateDeviceAgainstMeasure import EvaluateDeviceAgainstMeasure
from ..ExecutionContext import ExecutionContext


class EvaluateMeasure(AbstractCommand):
    """
    A command that queues device evaluation for any device controlled by given measure
    """

    def __init__(self, measure: SensorMeasure):
        self.measure = measure

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        device_control_repository = DeviceControlRepository(context.db_session)
        operating_mode = device_control_repository.get_mode_for(context.time_source.now())

        for device_control in device_control_repository.get_devices_controlled_by(self.measure.kind, operating_mode):
            context.command_queue.put_nowait(
                EvaluateDeviceAgainstMeasure(device_control.device_kind, operating_mode, self.measure)
            )
