from unittest import TestCase
from persistence import TargetTemperature


class TestTargetTemperature(TestCase):
    """
    Tests for target temperature class
    """
    def test_get_as_float(self):
        """
        Check whether conversion from centi to float works es expected
        """
        temperature = TargetTemperature(1, 2420)
        self.assertEqual(24.2, temperature.temperature)
