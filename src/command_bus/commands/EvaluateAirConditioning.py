import logging
from datetime import timedelta

from AirConditionerService import AirConditionerService
from models import SensorMeasure
from repositories import (
    AirConditionerPingRepository, AirConditionerStatusLogRepository, SensorMeasureRepository,
    TargetTemperatureRepository,
)
from .._AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class EvaluateAirConditioning(AbstractCommand):
    """
    A command that evaluates whether - given the temperatures and ait conditioning status - the air conditioning should
    be left intact, turned ON or OFF and performs the action.
    """

    def execute(self, context: ExecutionContext) -> None:
        """
        Executes the command
        """
        logging.debug("Evaluating air conditioning")

        air_conditioner = AirConditionerService(
            AirConditionerPingRepository(context.persistence),
            AirConditionerStatusLogRepository(context.persistence),
            context.time_source,
            context.radio
        )

        if not air_conditioner.is_available():
            # Air conditioner is off the grid, no need to evaluate
            air_conditioner.assume_off_status()
            return

        measure_repository = SensorMeasureRepository(context.persistence)
        current_measure = measure_repository.get_last_temperature(
            SensorMeasure.LIVING_ROOM,
            context.time_source.now() - timedelta(minutes=10)
        )

        if current_measure is None:
            # We don't know current temperature
            logging.warning('Attempted to evaluate air conditioning, but there is no current temperature measure')
            return

        target = TargetTemperatureRepository(context.persistence).get_target_temperature()
        logging.debug('Current t: %.2f, target t: %.2f', current_measure.temperature, target.temperature)

        if air_conditioner.is_turned_off() and target.is_temperature_above_range(current_measure.temperature):
            # Air conditioning should be turned ON
            if air_conditioner.can_turn_on():
                air_conditioner.turn_on()
                logging.info('Air conditioning TURNED ON')
                return
            else:
                # TODO: schedule turning on at first possible moment
                logging.info('Air conditioning should be turned ON, but AC is in the grace period')

        if air_conditioner.is_turned_on() and target.is_temperature_below_range(current_measure.temperature):
            # Air conditioning should be turned OFF
            if air_conditioner.can_turn_off():
                air_conditioner.turn_off()
                logging.info('Air conditioning TURNED OFF')
                return
            else:
                # TODO: schedule turning on at first possible moment
                logging.info('Air conditioning should be turned OFF, but AC is in the grace period')
