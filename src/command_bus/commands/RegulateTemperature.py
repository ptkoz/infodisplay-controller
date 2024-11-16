import logging
from datetime import timedelta
from devices import get_device_for_kind
from domain_types import DeviceKind
from persistence import (
    DevicePingRepository, DeviceStatusRepository, NounceRepository, SensorMeasure,
    SensorMeasureRepository, ThresholdTemperature,
)
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class RegulateTemperature(AbstractCommand):
    """
    Given the device and measure, determines whether device should be turned on/off
    """
    __TARGET_POWER_SAVE_DELTA: int = 15

    def __init__(
        self,
        device_kind: DeviceKind,
        measure: SensorMeasure,
        threshold_temperature: ThresholdTemperature
    ):
        self.device_kind = device_kind
        self.measure = measure
        self.threshold_temperature = threshold_temperature

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
            context.outbound_bus
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

        logging.debug(
            'Evaluating device %s against %s, current t: %.2f, target t: %.2f',
            self.device_kind.name,
            self.measure.kind.name,
            self.measure.temperature,
            self.threshold_temperature
        )

        if self.should_start_cooling_down(context, device.can_start_cool_down(), device.is_turned_on()):
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

        if self.should_start_warming_up(context, device.can_start_warm_up(), device.is_turned_on()):
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

    def should_start_warming_up(self, context: ExecutionContext, can_start: bool, consider_power_save: bool) -> bool:
        """
        Checks whether we should start warming up
        """
        if not can_start:
            return False

        if self.measure.temperature < self.threshold_temperature.warm_up_threshold:
            return True

        if consider_power_save and self.measure.temperature < self.threshold_temperature.power_save_threshold:
            last_above = SensorMeasureRepository(context.db_session).get_last_min(
                self.measure.kind,
                self.threshold_temperature.power_save_threshold
            )
            last_must_be_older_than = context.time_source.now() - timedelta(minutes=self.__TARGET_POWER_SAVE_DELTA)
            if last_above is not None and last_above.timestamp < last_must_be_older_than:
                return True

        return False

    def should_start_cooling_down(self, context: ExecutionContext, can_start: bool, consider_power_save: bool) -> bool:
        """
        Checks whether we should start cooling down
        """
        if not can_start:
            return False

        if self.measure.temperature > self.threshold_temperature.cool_down_threshold:
            return True

        if consider_power_save and self.measure.temperature > self.threshold_temperature.power_save_threshold:
            last_below = SensorMeasureRepository(context.db_session).get_last_max(
                self.measure.kind,
                self.threshold_temperature.power_save_threshold
            )
            last_must_be_older_than = context.time_source.now() - timedelta(minutes=self.__TARGET_POWER_SAVE_DELTA)
            if last_below is not None and last_below.timestamp < last_must_be_older_than:
                return True

        return False
