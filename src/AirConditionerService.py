import logging
import time
from datetime import datetime
from typing import Type
from persistence import AirConditionerPingRepository, AirConditionerStatus, AirConditionerStatusLogRepository
from radio_bus import OutboundMessage, Radio


# Service controlling our Dimplex air conditioner
class AirConditionerService:
    """
    Orchestrates work around controlling the air conditioner
    """

    MAX_INTERVAL_WITHOUT_PING = 180  # seconds
    """
    Minimum amount of time that needs to pass between turn off and turn on (and vice versa)
    """

    MIN_GRACE_PERIOD = 300  # seconds
    """
    After this amount of time without a ping we'll consider remote AC unit not available
    """

    def __init__(
        self,
        air_conditioner_ping_repository: AirConditionerPingRepository,
        air_conditioner_status_log_repository: AirConditionerStatusLogRepository,
        time_source: Type[datetime],
        radio: Radio
    ):
        self.__ping_repository = air_conditioner_ping_repository
        self.__status_log_repository = air_conditioner_status_log_repository
        self.__time_source = time_source
        self.__radio = radio

    def is_available(self) -> bool:
        """
        Checks if AirConditioner device is available online
        """
        last_ping = self.__ping_repository.get_last_ping()
        if last_ping is None:
            return False

        return (self.__time_source.now() - last_ping.timestamp).total_seconds() < self.MAX_INTERVAL_WITHOUT_PING

    def is_turned_on(self) -> bool:
        """
        Checks if air conditioner is currently turned on
        """
        current_status = self.__status_log_repository.get_current_status()
        return current_status == AirConditionerStatus.TURNED_ON

    def is_turned_off(self) -> bool:
        """
        Checks if air conditioner is currently turned on
        """
        current_status = self.__status_log_repository.get_current_status()
        return current_status is None or current_status == AirConditionerStatus.TURNED_OFF

    def can_turn_on(self) -> bool:
        """
        Can we turn on? (prevents turning on when we are in the grace period after turn off)
        """
        if not self.is_available():
            return False

        last_turned_off = self.__status_log_repository.get_last_turn_off()
        return (
            last_turned_off is None or
            (self.__time_source.now() - last_turned_off.timestamp).total_seconds() > self.MIN_GRACE_PERIOD
        )

    def can_turn_off(self) -> bool:
        """
        Can we turn off? (prevents turning off when we are in the grace period after turn on)
        """
        if not self.is_available():
            return False

        last_turned_on = self.__status_log_repository.get_last_turn_on()
        return (
            last_turned_on is None or
            (self.__time_source.now() - last_turned_on.timestamp).total_seconds() > self.MIN_GRACE_PERIOD
        )

    def assume_off_status(self) -> None:
        """
        Assumes air conditioner is off and persist that as state if necessary
        """
        last_status = self.__status_log_repository.get_current_status()
        if last_status is None or last_status == AirConditionerStatus.TURNED_ON:
            logging.warning("Assumed off status for AirConditioning")
            self.__status_log_repository.set_current_status(
                AirConditionerStatus.TURNED_OFF,
                self.__time_source.now()
            )

    def turn_on(self) -> None:
        """
        Turns on the air conditioner and records turned on status
        """
        if not self.can_turn_on():
            raise RuntimeError(
                'Attempting to turn ON the air conditioner while it is not available or in the grace period'
            )

        self.__status_log_repository.set_current_status(
            AirConditionerStatus.TURNED_ON,
            self.__time_source.now()
        )

        message = OutboundMessage(0xA2, 0x01)
        self.__radio.send(message)
        time.sleep(0.7)
        self.__radio.send(message)

    def turn_off(self) -> None:
        """
        Turns off the air conditioner and records turned on status
        """
        if not self.can_turn_off():
            raise RuntimeError(
                'Attempting to turn OFF the air conditioner while it is not available or in the grace period'
            )

        self.__status_log_repository.set_current_status(
            AirConditionerStatus.TURNED_OFF,
            self.__time_source.now()
        )

        message = OutboundMessage(0xA2, 0x02)
        self.__radio.send(message)
        time.sleep(0.7)
        self.__radio.send(message)
