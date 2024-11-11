from datetime import datetime
from queue import Queue
from typing import Type
from secrets import MY_ADDRESS
from domain_types import DeviceKind
from persistence import DevicePingRepository, DeviceStatusRepository, NounceRepository
from radio_bus import OutboundMessage
from ui import UiPublisher
from .AbstractDevice import AbstractDevice


class Heater(AbstractDevice):
    """
    Heating device
    """

    def __init__(
        self,
        device_ping_repository: DevicePingRepository,
        device_status_repository: DeviceStatusRepository,
        nounce_repository: NounceRepository,
        time_source: Type[datetime],
        publisher: UiPublisher,
        outbound_bus: Queue,
    ):
        super().__init__(
            DeviceKind.HEATING,
            device_ping_repository,
            device_status_repository,
            nounce_repository,
            time_source,
            publisher
        )
        self.outbound_bus = outbound_bus

    def can_start_cool_down(self) -> bool:
        """
        Checks whether the device is able to cool the temperature down, either by turning itself on or off
        """
        return self.is_turned_on()

    def is_in_cooling_grace_period(self) -> bool:
        """
        Checks whether device is currently in a grace period that prevents it from cooling down
        """
        return not self.can_turn_off()

    def start_cool_down(self) -> None:
        """
        Tells the device to start the cool down process
        """
        self.turn_off()

    def can_start_warm_up(self) -> bool:
        """
        Checks whether the device is able to warm the temperature up, either by turning itself on or off
        """
        return self.is_turned_off()

    def is_in_warming_grace_period(self) -> bool:
        """
        Checks whether device is currently in a grace period that prevents it from warming up
        """
        return not self.can_turn_on()

    def start_warm_up(self) -> None:
        """
        Tells device to start the warm-up process
        """
        self.turn_on()

    def turn_on(self) -> None:
        """
        Turns heater on and records turned on status
        """
        self._register_turn_on()

        message = OutboundMessage(
            MY_ADDRESS,
            DeviceKind.HEATING.value,
            0x01,
            self.nounce_repository.next_outbound_nounce(DeviceKind.HEATING.value)
        )
        self.outbound_bus.put_nowait(message)
        self.outbound_bus.put_nowait(message)

    def turn_off(self) -> None:
        """
        Turns off the heater and records turned off status
        """
        self._register_turn_off()

        message = OutboundMessage(
            MY_ADDRESS,
            DeviceKind.HEATING.value,
            0x02,
            self.nounce_repository.next_outbound_nounce(DeviceKind.HEATING.value)
        )
        self.outbound_bus.put_nowait(message)
        self.outbound_bus.put_nowait(message)
