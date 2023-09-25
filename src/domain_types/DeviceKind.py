from enum import Enum


class DeviceKind(Enum):
    """
    Available devices
    """
    COOLING = 0x90
    HEATING = 0x91
