from typing import Optional
from .Radio import Radio


class OutboundMessage:
    """
    Represents a message that can be sent through radio
    """

    def __init__(self, recipient: int, kind: int, data: Optional[bytes] = None):
        # narrow recipient & kind down to 1 byte length, as this is the maximum that can be sent
        recipient = min(recipient, 255)
        kind = min(kind, 255)

        message = bytearray()
        message.append(recipient)
        message.append(kind)

        # Having 255 byte limit for the whole message, we can't afford unencoded messages longer than 120 bytes.
        # Don't include the data whatsoever in such case.
        if data is not None and len(data) < 120:
            message.extend(data)

        self.encoded_data = bytearray()
        self.encoded_data.extend(Radio.MESSAGE_START_MARKER)  # every message starts with message start marker
        self.encoded_data.append(0)  # reserved for message size

        for b in message:
            if b & 0x80:
                # Highest bit is set, let's split this byte across two bytes with only 4 low bits set on each, to ensure
                # start marker doesn't occur anywhere in the data stream. Then flag first byte with "10" on highest bits
                # which doesn't collide with start marker, but can inform consumer those need to be joined when reading.
                self.encoded_data.append((b >> 4) | 0x80)
                self.encoded_data.append(b & 0x0F)

            else:
                # highest bit is not set, we can leave value unencoded
                self.encoded_data.append(b)

        self.encoded_data[1] = len(self.encoded_data) - 2  # minus start marker and the byte for size
