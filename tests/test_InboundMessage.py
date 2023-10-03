from struct import unpack
from unittest import TestCase
from radio_bus import InboundMessage


class TestInboundMessage(TestCase):
    """
    Test cases for inbound messages decoding
    """

    def test_message_incorrect_data(self):
        """
        Tests whether message with incorrect data is handled as expected
        """
        message = InboundMessage(
            b'\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f\x8c\x8f'
        )
        self.assertEqual(0, message.from_address)
        self.assertEqual(0, message.to_address)
        self.assertEqual(0, message.command)
        self.assertEqual(0, message.nounce)
        self.assertEqual(0, message.extended_bytes_length)
        self.assertFalse(message.is_valid(0))

    def test_message_without_data(self):
        """
        Tests whether message without data is decoded correctly
        """
        message = InboundMessage(
            b';\x8b\x00\x8a\x04\x88\x01\x89\x07JB\x89\x04\x8d\x0e\n/'
            b'\x12\x8b\x0ekyIkdt\x00\x8a\x01\x8a\x02\x02',
        )
        self.assertEqual(0xA1, message.from_address)
        self.assertEqual(0xA2, message.to_address)
        self.assertEqual(0x02, message.command)
        self.assertEqual(0x74646B, message.nounce)
        self.assertEqual(0, message.extended_bytes_length)
        self.assertTrue(message.is_valid(0x74646A))
        self.assertFalse(message.is_valid(0x74646C))

    def test_message_without_data_incorrect_hmac(self):
        """
        Tests whether message without data is decoded correctly
        """
        message = InboundMessage(
            b';\x8b\x00\x8b\x04\x88\x01\x89\x07JB\x89\x04\x8d\x0e\n/'
            b'\x12\x8b\x0ekyIkdt\x00\x8a\x01\x8a\x02\x02',
        )
        self.assertEqual(0xA1, message.from_address)
        self.assertEqual(0xA2, message.to_address)
        self.assertEqual(0x02, message.command)
        self.assertEqual(0x74646B, message.nounce)
        self.assertEqual(0, message.extended_bytes_length)
        self.assertFalse(message.is_valid(0))

    def test_message_with_data(self):
        """
        Tests whether message with data is decoded correctly
        """
        message = InboundMessage(
            b'\x88\x06\x8f\x0c\x8b\x0f\x8f\r\x7fo\\\x89\x04gP\x0e`\x8c\rM\x88\x058kdt'
            b'\x00\x01}~\x8f\x0f\x7f\x8c\x00\x88\x00',
        )
        self.assertEqual(0x01, message.from_address)
        self.assertEqual(0x7D, message.to_address)
        self.assertEqual(0x7E, message.command)
        self.assertEqual(0x74646B, message.nounce)
        self.assertEqual(4, message.extended_bytes_length)
        self.assertTrue(message.is_valid(0x74646A))
        self.assertFalse(message.is_valid(0x74646C))

        [data] = unpack('<L', message.extended_bytes)
        self.assertEqual(0x80C07FFF, data)

    def test_message_with_data_incorrect_hmac(self):
        """
        Tests whether message with data is decoded correctly
        """
        message = InboundMessage(
            b'\x88\x06\x8e\x0c\x8b\x0f\x8f\r\x7fo\\\x89\x04gP\x0e`\x8c\rM\x88\x058kdt'
            b'\x00\x01}~\x8f\x0f\x7f\x8c\x00\x88\x00',
        )
        self.assertEqual(0x7D, message.to_address)
        self.assertEqual(0x7E, message.command)
        self.assertEqual(0x74646B, message.nounce)
        self.assertEqual(4, message.extended_bytes_length)
        self.assertFalse(message.is_valid(0))

        [data] = unpack('<L', message.extended_bytes)
        self.assertEqual(0x80C07FFF, data)
