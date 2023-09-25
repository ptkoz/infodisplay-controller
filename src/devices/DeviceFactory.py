from datetime import datetime
from typing import Type
from domain_types import DeviceKind
from persistence import DevicePingRepository, DeviceStatusRepository
from radio_bus import Radio
from ui import Publisher
from .AbstractDevice import AbstractDevice
from .AirConditioner import AirConditioner
from .Heater import Heater

def get_device_for_kind(
    kind: DeviceKind,
    device_ping_repository: DevicePingRepository,
    device_status_repository: DeviceStatusRepository,
    time_source: Type[datetime],
    publisher: Publisher,
    radio: Radio,
) -> AbstractDevice:
    """
    Returns device implementation for given kind
    """
    if kind == DeviceKind.COOLING:
        return AirConditioner(device_ping_repository, device_status_repository, time_source, publisher, radio)
    if kind == DeviceKind.HEATING:
        return Heater(device_ping_repository, device_status_repository, time_source, publisher, radio)

    raise RuntimeError(f"Unknown device kind: {kind:#x}")
