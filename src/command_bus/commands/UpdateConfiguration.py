import logging
from persistence import AwayStatusRepository, ThresholdTemperatureRepository, DeviceControlRepository
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus
from ui import ThresholdTemperatureUpdate, DeviceControlUpdate, AwayStatusUpdate
from .AbstractCommand import AbstractCommand
from .EvaluateDevice import EvaluateDevice
from ..ExecutionContext import ExecutionContext


class UpdateConfiguration(AbstractCommand):
    """
    A command that updates the control measures and threshold temperatures
    """

    def __init__(self, data: dict):
        self.data = data

    def execute(self, context: ExecutionContext) -> None:
        """
        Send all the required data to the client.
        """
        away_status_repository = AwayStatusRepository(context.db_session)
        if self.data["isAway"] is not None and self.data["isAway"] != away_status_repository.is_away():
            away_status_repository.set_away_status(
                context.time_source.now(),
                PowerStatus.TURNED_ON if self.data["isAway"] else PowerStatus.TURNED_OFF,
            )
            context.publisher.publish(AwayStatusUpdate(away_status_repository.is_away()))

        threshold_temperature_repository = ThresholdTemperatureRepository(context.db_session)
        if self.data["thresholdTemperature"] is not None:
            for device_key in self.data["thresholdTemperature"]:
                device_kind = DeviceKind(int(device_key))
                for mode_key in self.data["thresholdTemperature"][device_key]:
                    operating_mode = OperatingMode(mode_key)
                    threshold_temperature = threshold_temperature_repository.set_threshold_temperature(
                        device_kind,
                        operating_mode,
                        self.data["thresholdTemperature"][device_key][mode_key]
                    )

                    logging.debug(
                        "Threshold %s temperature in %s set to %f",
                        device_kind.name,
                        operating_mode.name,
                        threshold_temperature.temperature
                    )
                    context.publisher.publish(ThresholdTemperatureUpdate(threshold_temperature))

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
