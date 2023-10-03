import logging

from persistence import TargetTemperatureRepository, DeviceControlRepository
from domain_types import DeviceKind, MeasureKind, OperatingMode
from ui import TargetTemperatureUpdate, DeviceControlUpdate
from .AbstractCommand import AbstractCommand
from .EvaluateDevice import EvaluateDevice
from ..ExecutionContext import ExecutionContext


class UpdateConfiguration(AbstractCommand):
    """
    A command that updates the control measures and target temperatures
    """

    def __init__(self, data: dict):
        self.data = data

    def execute(self, context: ExecutionContext) -> None:
        """
        Send all the required data to the client.
        """
        target_temperature_repository = TargetTemperatureRepository(context.db_session)
        if self.data["targetTemperature"] is not None:
            for device_key in self.data["targetTemperature"]:
                device_kind = DeviceKind(int(device_key))
                for mode_key in self.data["targetTemperature"][device_key]:
                    operating_mode = OperatingMode(mode_key)
                    target_temperature = target_temperature_repository.set_target_temperature(
                        device_kind,
                        operating_mode,
                        self.data["targetTemperature"][device_key][mode_key]
                    )

                    logging.debug(
                        "Target %s temperature in %s set to %f",
                        device_kind.name,
                        operating_mode.name,
                        target_temperature.temperature
                    )
                    context.publisher.publish(TargetTemperatureUpdate(target_temperature))

        device_control_repository = DeviceControlRepository(context.db_session)
        if self.data["controlMeasures"] is not None:
            for device_key in self.data["controlMeasures"]:
                device_kind = DeviceKind(int(device_key))
                for mode_key in self.data["controlMeasures"][device_key]:
                    operating_mode = OperatingMode(mode_key)
                    controlling_measures = [MeasureKind(i) for i in self.data["controlMeasures"][device_key][mode_key]]
                    device_control_repository.set_controlling_measures(
                        device_kind,
                        operating_mode,
                        controlling_measures
                    )

                    logging.debug(
                        "Device %s at %s is now controlled by %d measures",
                        device_kind.name,
                        operating_mode.name,
                        len(controlling_measures)
                    )

                context.publisher.publish(
                    DeviceControlUpdate(
                        device_kind,
                        device_control_repository.get_measures_controlling(device_kind)
                    )
                )

        for kind in DeviceKind:
            context.command_queue.put_nowait(EvaluateDevice(kind))
