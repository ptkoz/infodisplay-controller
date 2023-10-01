from hashlib import blake2s
from struct import pack
from typing import Optional
from secrets import HMAC_KEY
from .MessageStartMarker import MESSAGE_START_MARKER


class OutboundMessage:
    """
    Represents a message that can be sent through radio
    """

    def __init__(self, from_address: int, to_address: int, command: int, nounce: int, data: Optional[bytes] = None):
        # narrow from, to & command down to 1 byte length, as this is the maximum that we can send
        from_address = min(from_address, 255)
        to_address = min(to_address, 255)
        command = min(command, 255)
        # narrow nounce down to 4 bytes in length (unsigned), as this is the maximum that we can send
        nounce = min(nounce, 4294967295)

        message = bytearray()
        message.extend(pack("<L", nounce))
        message.append(from_address)
        message.append(to_address)
        message.append(command)

        # Having 255 byte limit for the whole message, we can't afford unencoded messages longer than 100 bytes.
        # Don't include the data whatsoever in such case.
        if data is not None and len(data) < 100:
            message.extend(data)

        encoded_data = bytearray()
        encoded_data.extend(MESSAGE_START_MARKER)  # every message starts with message start marker
        encoded_data.append(0)  # reserved for message size

        blake = blake2s(key=HMAC_KEY, digest_size=16)
        blake.update(message)

        for b in blake.digest() + message:
            if b & 0x80:
                # Highest bit is set, let's split this byte across two bytes with only 4 low bits set on each, to ensure
                # start marker doesn't occur anywhere in the data stream. Then flag first byte with "10" on highest bits
                # which doesn't collide with start marker, but can inform consumer those need to be joined when reading.
                encoded_data.append((b >> 4) | 0x80)
                encoded_data.append(b & 0x0F)

            else:
                # highest bit is not set, we can leave value unencoded
                encoded_data.append(b)

        encoded_data[1] = len(encoded_data) - 2  # minus start marker and the byte for size
        self.encoded_data = bytes(encoded_data)
