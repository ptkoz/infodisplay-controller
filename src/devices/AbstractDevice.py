import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Type
from domain_types import DeviceKind, PowerStatus
from persistence import DeviceStatusRepository, DevicePingRepository, NounceRepository
from ui import UiPublisher, DeviceStatusUpdate


class AbstractDevice(ABC):
    """
    Abstract temperature - controlling device
    """

    MAX_INTERVAL_WITHOUT_PING = 180  # seconds
    """
    After this amount of time without a ping we'll consider remote AC unit not available
    """

    MIN_GRACE_PERIOD = 300  # seconds
    """
    Minimum amount of time that needs to pass between turn off and turn on (and vice versa)
    """

    def __init__(
        self,
        kind: DeviceKind,
        device_ping_repository: DevicePingRepository,
        device_status_repository: DeviceStatusRepository,
        nounce_repository: NounceRepository,
        time_source: Type[datetime],
        publisher: UiPublisher
    ):
        self.kind = kind
        self.device_ping_repository = device_ping_repository
        self.device_status_repository = device_status_repository
        self.nounce_repository = nounce_repository
        self.time_source = time_source
        self.publisher = publisher

    def is_available(self) -> bool:
        """
        Checks if device is available online
        """
        last_ping = self.device_ping_repository.get_last_ping(self.kind)
        if last_ping is None:
            return False

        return (self.time_source.now() - last_ping.timestamp).total_seconds() < self.MAX_INTERVAL_WITHOUT_PING

    def assume_off_status(self) -> None:
        """
        Assumes device is off and persist that as state if necessary
        """
        last_status = self.device_status_repository.get_current_status(self.kind)
        if last_status is None or last_status == PowerStatus.TURNED_ON:
            logging.warning("Assumed off status for device %s", self.kind.name)
            self.device_status_repository.set_current_status(self.kind, PowerStatus.TURNED_OFF, self.time_source.now())
            self.publisher.publish(DeviceStatusUpdate(self.kind, False))

    def is_turned_on(self) -> bool:
        """
        Checks if device is currently turned on
        """
        return self.device_status_repository.get_current_status(self.kind) == PowerStatus.TURNED_ON

    def is_turned_off(self) -> bool:
        """
        Checks if device is currently turned off
        """
        return self.device_status_repository.get_current_status(self.kind) == PowerStatus.TURNED_OFF

    def can_turn_on(self) -> bool:
        """
        Can we turn on? (prevents turning on when device is in the grace period after turn off)
        """
        if not self.is_available():
            return False

        last_turn_off = self.device_status_repository.get_last_turn_off(self.kind)
        return (
            last_turn_off is None or
            (self.time_source.now() - last_turn_off.timestamp).total_seconds() > self.MIN_GRACE_PERIOD
        )

    def can_turn_off(self) -> bool:
        """
        Can we turn off? (prevents turning off when device is in the grace period after turn on)
        """
        if not self.is_available():
            return False

        last_turn_on = self.device_status_repository.get_last_turn_on(self.kind)
        return (
            last_turn_on is None or
            (self.time_source.now() - last_turn_on.timestamp).total_seconds() > self.MIN_GRACE_PERIOD
        )

    @abstractmethod
    def turn_on(self) -> None:
        """
        Turns the device on
        """

    @abstractmethod
    def turn_off(self) -> None:
        """
        Turns the device off
        """

    def _register_turn_on(self) -> None:
        """
        Register that the device has been turned on
        """
        if not self.can_turn_on():
            raise RuntimeError(
                f"Turn ON device {self.kind.name:s} while it is not available or in the grace period is not possible"
            )

        self.device_status_repository.set_current_status(self.kind, PowerStatus.TURNED_ON, self.time_source.now())
        self.publisher.publish(DeviceStatusUpdate(self.kind, True))

    def _register_turn_off(self) -> None:
        """
        Register that the device has been turned off
        """
        if not self.can_turn_off():
            raise RuntimeError(
                f"Turn OFF device {self.kind.name:s} while it is not available or in the grace period is not possible"
            )

        self.device_status_repository.set_current_status(self.kind, PowerStatus.TURNED_OFF, self.time_source.now())
        self.publisher.publish(DeviceStatusUpdate(self.kind, False))

    @abstractmethod
    def can_start_cool_down(self) -> bool:
        """
        Checks whether the device is able to cool the temperature down, either by turning itself on or off
        """

    @abstractmethod
    def is_in_cooling_grace_period(self) -> bool:
        """
        Checks whether device is currently in a grace period that prevents it from cooling down
        """

    @abstractmethod
    def start_cool_down(self) -> None:
        """
        Tells the device to start the cool down process
        """

    @abstractmethod
    def can_start_warm_up(self) -> bool:
        """
        Checks whether the device is able to warm the temperature up, either by turning itself on or off
        """

    @abstractmethod
    def is_in_warming_grace_period(self) -> bool:
        """
        Checks whether device is currently in a grace period that prevents it from warming up
        """

    @abstractmethod
    def start_warm_up(self) -> None:
        """
        Tells device to start the warm-up process
        """
