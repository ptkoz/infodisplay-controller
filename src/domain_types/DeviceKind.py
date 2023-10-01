from enum import Enum


class DeviceKind(Enum):
    """
    Available devices
    """
    COOLING = 0x30
    HEATING = 0x31
