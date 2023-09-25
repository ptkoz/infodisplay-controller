from enum import Enum


class MeasureKind(Enum):
    """
    Available measure kinds
    """
    OUTDOOR = 0x41
    LIVING_ROOM = 0x20
    BEDROOM = 0x21
