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


class TestEvaluateMeasure(TestCase):
    """
    Test case for device evaluation
    """
    NOW = datetime(2023, 9, 13, 11, 35, 15)
    TURN_ON_BYTES = \
        b'\xff"\x07~X\x88\r\x88\x04\x8b\x02\x8a\x04\x8e\x03\x8a\x07\x8e\r\x8c\x06\x8a\x0e\x89\n\x8d\n\x011' \
        b'\x01\x00\x00\x00\x100\x01'

    TURN_OFF_BYTES = \
        b'\xff\x1a?y\x8b\x03rG\x8a\n\x89\n\x027>U7\x012w<\x01\x00\x00\x00\x100\x02'

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

    def test_regulated_device_is_turned_on(self) -> None:
        """
        Confirms it turns on regulated device when temperature is below desired range (18.7 - 19.3)
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_OFF))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 18.7))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))

    def test_regulated_device_is_turned_off(self) -> None:
        """
        Confirms it turns off regulated device when temperature is above desired range (18.7 - 19.3)
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.31))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))

    def test_heating_remains_on_when_in_range_but_below_target(self) -> None:
        """
        Confirms it doesn't change heating status when it was turned on and temperature is IN desired range for
        30 minutes, but below target temperature
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 18.53))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 18.85))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 18.86))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 18.87))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 18.9))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_remains_on_when_in_range_but_above_target(self) -> None:
        """
        Confirms it doesn't change cooling status when it was turned on and temperature is IN desired range for
        30 minutes, but above target temperature
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 25.31))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 25.10))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 25.08))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 25.06))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 25.04))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))

    def test_heating_is_turned_off_when_in_range_but_above_target_for_15minutes(self) -> None:
        """
        Confirms it turns off heating when temperature is above target temperature for at least 15 minutes.
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))

        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 18.69))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 19.85))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 19.07))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 19.08))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.1))

        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.HEATING))

    def test_cooling_is_turned_off_when_in_range_but_below_target_for_15minutes(self) -> None:
        """
        Confirms it turns off heating when temperature is below target temperature for at least 15 minutes.
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))

        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 25.3))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 24.99))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 24.98))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 24.97))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 24.96))

        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_OFF, status_repository.get_current_status(DeviceKind.COOLING))


    def test_heating_remains_on_when_above_target_for_less_than_15minutes(self) -> None:
        """
        Confirms it doesn't change heating status when it was turned on and temperature is above target temperature
        for less than 15 minutes
        """
        self.session.add(DevicePing(DeviceKind.HEATING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.HEATING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 18.98))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 18.99))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 19.03))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 19.03))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 19.04))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))
        self.execute(DeviceKind.HEATING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.HEATING))


    def test_cooling_remains_on_when_below_target_for_less_than_15minutes(self) -> None:
        """
        Confirms it doesn't change cooling status when it was turned on and temperature is above target temperature
        for less than 15 minutes
        """
        self.session.add(DevicePing(DeviceKind.COOLING, self.NOW - timedelta(minutes=1)))
        self.session.add(DeviceStatus(DeviceKind.COOLING, self.NOW - timedelta(minutes=25), PowerStatus.TURNED_ON))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=20), MeasureKind.BEDROOM, 25.02))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=15), MeasureKind.BEDROOM, 25.03))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=10), MeasureKind.BEDROOM, 24.99))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5), MeasureKind.BEDROOM, 24.98))
        self.session.add(SensorMeasure(self.NOW, MeasureKind.BEDROOM, 24.97))
        status_repository = DeviceStatusRepository(self.session)

        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
        self.execute(DeviceKind.COOLING)
        self.assertEqual(PowerStatus.TURNED_ON, status_repository.get_current_status(DeviceKind.COOLING))
