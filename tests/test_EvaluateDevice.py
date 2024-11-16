import logging
from datetime import datetime, timedelta
from queue import Empty, Queue
from unittest import TestCase
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus import EvaluateDevice
from command_bus.ExecutionContext import ExecutionContext
from persistence import (
    AbstractBase, DeviceControl, DevicePing, DeviceStatus, DeviceStatusRepository, SensorMeasure,
    ThresholdTemperature,
)
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus


class TestEvaluateDevice(TestCase):
    """
    Test case for device evaluation
    """
    NOW = datetime(2023, 9, 13, 11, 35, 15)

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)
        logging.disable(logging.CRITICAL)

        self.queue: Queue = Queue()
        self.mock_datetime = Mock()
        self.mock_datetime.now = Mock(return_value=self.NOW)
        self.session = Session(engine)

        self.session.add(ThresholdTemperature(DeviceKind.COOLING, OperatingMode.DAY, 2500))
        self.session.add(ThresholdTemperature(DeviceKind.COOLING, OperatingMode.NIGHT, 2000))
        self.session.add(ThresholdTemperature(DeviceKind.HEATING, OperatingMode.DAY, 1900))
        self.session.add(ThresholdTemperature(DeviceKind.HEATING, OperatingMode.NIGHT, 1800))

        # noinspection PyTypeChecker
        self.context = ExecutionContext(
            self.session,
            self.queue,
            Queue(),
            Mock(),
            self.mock_datetime,
        )

        def is_status_log_eq(first: DeviceStatus, second: DeviceStatus, msg=None) -> None:
            self.assertEqual(first.kind, second.kind, msg)
            self.assertEqual(first.status, second.status, msg)
            self.assertEqual(first.timestamp, second.timestamp, msg)

        self.addTypeEqualityFunc(DeviceStatus, is_status_log_eq)

    def tearDown(self) -> None:
        self.session.close()

    def execute(self, device_kind: DeviceKind):
        """
        Helper function that executes the command with given measure and then also executes
        all the commands that have been enqueued by the execution.
        """
        EvaluateDevice(device_kind).execute(self.context)
        try:
            while True:
                self.context.command_queue.get_nowait().execute(self.context)
        except Empty:
            pass

    def test_unregulated_device_is_off(self) -> None:
        """
        Confirms it does nothing for unregulated device that is turned off
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_OFF))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))

    def test_unregulated_device_is_on(self) -> None:
        """
        Confirms it turns off unregulated device that is on
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))

    def test_heating_device_is_turned_on(self) -> None:
        """
        Confirms it turns on regulated heating device when temperature is below configured threshold
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_OFF))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 18.99))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))

    def test_heating_device_is_turned_off(self) -> None:
        """
        Confirms it turns off regulated heating device when temperature is above heating range (19.0 - 19.5)
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.51))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_device_is_turned_on(self) -> None:
        """
        Confirms it turns on regulated cooling device when temperature is above configured threshold
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_OFF))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.LIVING_ROOM, 25.01))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))

    def test_cooling_device_is_turned_off(self) -> None:
        """
        Confirms it turns off regulated cooling device when temperature is below cooling range (24.5 - 25.0)
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.LIVING_ROOM, 24.49))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))

    def test_heating_remains_on_when_stays_long_in_range_but_below_power_save_threshold(self) -> None:
        """
        Confirms it doesn't change heating status when it was turned on and temperature remains in heating range for
        30 minutes, but below power save threshold temperature
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 18.99))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 19.25))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 19.25))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 19.25))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.25))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_remains_on_when_stays_long_in_range_but_above_power_save_threshold(self) -> None:
        """
        Confirms it doesn't change cooling status when it was turned on and temperature remains in cooling range for
        30 minutes, but above power save threshold temperature
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 25.01))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 24.75))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 24.75))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 24.75))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 24.75))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))

    def test_heating_is_turned_off_when_stays_long_in_range_above_power_save_threshold(self) -> None:
        """
        Confirms it turns off heating when temperature is above power save threshold temperature for at least 15
        minutes, even though the temperature is still in heating range
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))

        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 18.99))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 19.26))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 19.27))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 19.28))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.29))

        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_is_turned_off_when_stays_long_in_range_below_power_save_threshold(self) -> None:
        """
        Confirms it turns off heating when temperature is below power save threshold temperature for at least 15
        minutes, even though the temperature is still in cooling range
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))

        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 25.1))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 24.74))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 24.73))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 24.72))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 24.71))

        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))

    def test_heating_remains_on_when_stays_long_in_range_and_above_power_save_threshold_but_not_enough(self) -> None:
        """
        Confirms it doesn't change heating status when it was turned on and temperature remains in heating range for
        15 minutes, but only 10 minutes above power save threshold temperature
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 19.24))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 19.25))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 19.26))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 19.27))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.28))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_remains_on_when_stays_long_in_range_and_below_power_save_threshold_but_not_enough(self) -> None:
        """
        Confirms it doesn't change cooling status when it was turned on and temperature remains in cooling range for
        15 minutes, but only 10 minutes below power save threshold temperature
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 24.76))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 24.75))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 24.74))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 24.73))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 24.72))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
