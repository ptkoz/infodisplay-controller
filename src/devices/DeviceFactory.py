from datetime import datetime
from queue import Queue
from typing import Type
from domain_types import DeviceKind
from persistence import DevicePingRepository, DeviceStatusRepository, NounceRepository
from ui import UiPublisher
from .AbstractDevice import AbstractDevice
from .AirConditioner import AirConditioner
from .Heater import Heater


def get_device_for_kind(
    kind: DeviceKind,
    device_ping_repository: DevicePingRepository,
    device_status_repository: DeviceStatusRepository,
    nounce_repository: NounceRepository,
    time_source: Type[datetime],
    publisher: UiPublisher,
    outbound_bus: Queue,
) -> AbstractDevice:
    """
    Returns device implementation for given kind
    """
    if kind == DeviceKind.COOLING:
        return AirConditioner(
            device_ping_repository,
            device_status_repository,
            nounce_repository,
            time_source,
            publisher,
            outbound_bus
        )
    if kind == DeviceKind.HEATING:
        return Heater(
            device_ping_repository,
            device_status_repository,
            nounce_repository,
            time_source,
            publisher,
            outbound_bus
        )

    raise RuntimeError(f"Unknown device kind: {kind:#x}")
