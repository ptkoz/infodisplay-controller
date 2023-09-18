from __future__ import annotations
from typing import Optional
from .Radio import Radio


class InboundMessage:
    """
    Represents an incoming radio message
    """

    def __init__(self, data: bytes):
        """
        Creates inbound message out of decoded bytes
        """
        result = bytearray()

        i = 0
        while i < len(data):
            if data[i] & 0x80 and i < len(data) - 1:
                result.append(
                    ((data[i] & 0x0F) << 4) | (data[i + 1])
                )
                i += 1
            else:
                result.append(data[i])

            i += 1

        self.recipient: int = result[0]
        self.kind: int = result[1]
        self.data: bytes = bytes(result[2:])
        self.length: int = len(self.data)

    @staticmethod
    def receive_from_radio(radio: Radio, size: int) -> Optional[InboundMessage]:
        """
        Attempts to get a message of given size from radio interface
        """
        radio.serial.timeout = 10
        message = radio.serial.read(size)

        if len(message) != size:
            return None

        return InboundMessage(message)
