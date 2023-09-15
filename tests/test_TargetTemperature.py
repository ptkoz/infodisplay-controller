from unittest import TestCase

from models import TargetTemperature


class TestTargetTemperature(TestCase):
    def test_get_as_float(self):
        temperature = TargetTemperature(1, 2420)
        self.assertEqual(24.2, temperature.temperature)
