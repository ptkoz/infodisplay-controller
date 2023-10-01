from unittest import TestCase
from radio_bus import OutboundMessage


class TestOutboundMessage(TestCase):
    """
    Test cases for outbound messages encoding
    """

    def test_message_without_data(self):
        """
        Tests whether message without data is encoded correctly and doesn't contain a single start marker
        """
        message = OutboundMessage(0xA1, 0xA2, 0x02, 0x74646B)

        self.assertEqual(34, len(message.encoded_data))
        self.assertEqual(
            b'\xff ;\x8b\x00\x8a\x04\x88\x01\x89\x07JB\x89\x04\x8d\x0e\n/'
            b'\x12\x8b\x0ekyIkdt\x00\x8a\x01\x8a\x02\x02',
            message.encoded_data
        )
        self.assertEqual(0xC0, message.encoded_data[0] & 0xC0)
        for byte in message.encoded_data[1:]:
            self.assertNotEqual(0xC0, byte & 0xC0)

    def test_message_with_data(self):
        """
        Tests whether message with data is encoded correctly and doesn't contain a single start marker
        """
        data = bytearray(4)
        data[0] = 0xFF
        data[1] = 0x7F
        data[2] = 0xC0
        data[3] = 0x80
        message = OutboundMessage(0x01, 0x7D, 0x7E, 0x74646B, data)

        self.assertEqual(39, len(message.encoded_data))

        self.assertEqual(
            b'\xff%\x88\x06\x8f\x0c\x8b\x0f\x8f\r\x7fo\\\x89\x04gP\x0e`\x8c\rM\x88\x058kdt'
            b'\x00\x01}~\x8f\x0f\x7f\x8c\x00\x88\x00',
            message.encoded_data
        )

        self.assertEqual(0xC0, message.encoded_data[0] & 0xC0)
        for byte in message.encoded_data[1:]:
            self.assertNotEqual(0xC0, byte & 0xC0)
