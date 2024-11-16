from unittest import TestCase
from domain_types import DeviceKind, OperatingMode
from persistence import ThresholdTemperature


class TestThresholdTemperature(TestCase):
    """
    Tests for target temperature class
    """
    def test_cooling_threshold(self):
        """
        Test threshold for cooling device
        """
        temperature = ThresholdTemperature(DeviceKind.COOLING, OperatingMode.NIGHT, 2420)
        self.assertEqual(24.2, temperature.temperature)
        self.assertEqual(24.2, temperature.cool_down_threshold)
        self.assertEqual(23.7, temperature.warm_up_threshold)
        self.assertEqual(23.95, temperature.power_save_threshold)

    def test_heating_threshold(self):
        """
        Test threshold for heating device
        """
        temperature = ThresholdTemperature(DeviceKind.HEATING, OperatingMode.NIGHT, 2420)
        self.assertEqual(24.2, temperature.temperature)
        self.assertEqual(24.2, temperature.warm_up_threshold)
        self.assertEqual(24.7, temperature.cool_down_threshold)
        self.assertEqual(24.45, temperature.power_save_threshold)

    def test_unknown_threshold(self):
        """
        Test threshold for unknown device
        """
        temperature = ThresholdTemperature(0x00, OperatingMode.NIGHT, 2420)
        self.assertEqual(24.2, temperature.temperature)
        self.assertEqual(23.95, temperature.warm_up_threshold)
        self.assertEqual(24.45, temperature.cool_down_threshold)
        self.assertEqual(24.2, temperature.power_save_threshold)
