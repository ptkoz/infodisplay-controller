from unittest import TestCase
from domain_types import DeviceKind, OperatingMode
from persistence import TargetTemperature


class TestTargetTemperature(TestCase):
    """
    Tests for target temperature class
    """
    def test_get_as_float(self):
        """
        Check whether conversion from centi to float works es expected
        """
        temperature = TargetTemperature(DeviceKind.HEATING, OperatingMode.NIGHT, 2420)
        self.assertEqual(24.2, temperature.temperature)
