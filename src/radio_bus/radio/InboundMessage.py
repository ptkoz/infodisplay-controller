from __future__ import annotations
from hashlib import blake2s
from struct import unpack
from typing import Optional
from secrets import HMAC_KEY
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

        self.__is_hmac_valid: bool
        self.nounce: int
        self.fromAddress: int
        self.toAddress: int
        self.command: int
        self.extended_bytes: bytes
        self.extended_bytes_length: int

        if len(data) >= 23:
            blake = blake2s(key=HMAC_KEY, digest_size=16)
            blake.update(result[16:])

            self.__is_hmac_valid = blake.digest() == result[:16]
            [self.nounce] = unpack("<L", result[16:20])
            self.from_address = result[20]
            self.to_address = result[21]
            self.command = result[22]
            self.extended_bytes = bytes(result[23:])
            self.extended_bytes_length = len(self.extended_bytes)
        else:
            self.__is_hmac_valid = False
            self.nounce = 0
            self.from_address = 0
            self.to_address = 0
            self.command = 0
            self.extended_bytes = bytes()
            self.extended_bytes_length = 0

    def is_valid(self, last_inbound_nounce: int):
        """
        Confirms message is authenticated, valid and hasn't been repeated (monotonically increasing nounce
        hasn't been used before)
        """
        return self.__is_hmac_valid and last_inbound_nounce < self.nounce

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
