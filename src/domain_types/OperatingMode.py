from enum import Enum


class OperatingMode(Enum):
    """
    Available operating modes
    """
    DAY = "day"  # comfort operating mode
    NIGHT = "night"  # economic operating mode
