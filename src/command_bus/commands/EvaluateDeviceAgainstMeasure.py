import logging
from devices import get_device_for_kind
from domain_types import DeviceKind, OperatingMode
from persistence import (
    DevicePingRepository, DeviceStatusRepository, NounceRepository, SensorMeasure, TargetTemperatureRepository,
)
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class EvaluateDeviceAgainstMeasure(AbstractCommand):
    """
    Given the device and measure, determines whether device should be turned on/off
    """

    def __init__(self, device_kind: DeviceKind, operating_mode: OperatingMode, measure: SensorMeasure):
        self.device_kind = device_kind
        self.operating_mode = operating_mode
        self.measure = measure

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        device = get_device_for_kind(
            self.device_kind,
            DevicePingRepository(context.db_session),
            DeviceStatusRepository(context.db_session),
            NounceRepository(context.db_session),
            context.time_source,
            context.publisher,
            context.radio
        )

        if not device.is_available():
            # Device is off the grid, no need to evaluate
            logging.debug(
                "Skipped evaluation of %s against %s because device is offline",
                self.device_kind.name,
                self.measure.kind.name
            )
            device.assume_off_status()
            return

        logging.debug("Evaluating device %s against %s", self.device_kind.name, self.measure.kind.name)

        target = TargetTemperatureRepository(context.db_session).get_target_temperature(
            self.device_kind,
            self.operating_mode
        )

        logging.debug('Current t: %.2f, target t: %.2f', self.measure.temperature, target.temperature)

        if target.is_temperature_above_range(self.measure.temperature) and device.can_cool_down():
            # device should start cooling down
            if device.is_in_cooling_grace_period():
                # to do: schedule cooling down at first possible moment
                logging.info(
                    'Device %s should be cooling down, but it is in the cooling grace period',
                    self.device_kind.name
                )

                return

            device.start_cool_down()
            logging.info('Device %s started COOLING DOWN', self.device_kind.name)

        if target.is_temperature_below_range(self.measure.temperature) and device.can_warm_up():
            # device should start warming up
            if device.is_in_warming_grace_period():
                # to do: schedule warming up at first possible moment
                logging.info(
                    'Device %s should be warming up, but it is in the warming grace period',
                    self.device_kind.name
                )
                return

            device.start_warm_up()
            logging.info('Device %s started WARMING UP', self.device_kind.name)
