import logging
from devices import get_device_for_kind
from domain_types import DeviceKind
from persistence import DevicePingRepository, DeviceStatusRepository, NounceRepository, SensorMeasure
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class RegulateTemperature(AbstractCommand):
    """
    Given the device and measure, determines whether device should be turned on/off
    """
    __BOUNDARY: float = 0.3

    def __init__(
        self,
        device_kind: DeviceKind,
        measure: SensorMeasure,
        target_temperature: float
    ):
        self.device_kind = device_kind
        self.measure = measure
        self.target_temperature = target_temperature

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
            self.target_temperature
        )

        if self.is_measure_above_target_range(self.measure, self.target_temperature) and device.can_cool_down():
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

        if self.is_measure_below_target_range(self.measure, self.target_temperature) and device.can_warm_up():
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

    def is_measure_above_target_range(self, measure: SensorMeasure, target_temperature: float) -> bool:
        """
        Checks if given temperature is higher than the threshold that enables AC
        """
        return measure.temperature > target_temperature + self.__BOUNDARY

    def is_measure_below_target_range(self, measure: SensorMeasure, target_temperature: float) -> bool:
        """
        Checks if given temperature is lower than the threshold that disables AC
        """
        return measure.temperature < target_temperature - self.__BOUNDARY
