import logging
from datetime import datetime, timedelta
from queue import Empty, Queue
from unittest import TestCase
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus import EvaluateMeasure
from command_bus.ExecutionContext import ExecutionContext
from persistence import AbstractBase, DeviceControl, DevicePing, DeviceStatus, SensorMeasure, TargetTemperature
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus


class TestEvaluateMeasure(TestCase):
    """
    Test case for air conditioning evaluation
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

        self.outbound_bus: Queue = Queue()
        self.mock_datetime = Mock()
        self.mock_datetime.now = Mock(return_value=self.NOW)
        self.session = Session(engine)

        self.session.add(TargetTemperature(DeviceKind.COOLING, OperatingMode.DAY, 2500))
        self.session.add(TargetTemperature(DeviceKind.COOLING, OperatingMode.NIGHT, 2000))
        self.session.add(TargetTemperature(DeviceKind.HEATING, OperatingMode.DAY, 1900))
        self.session.add(TargetTemperature(DeviceKind.HEATING, OperatingMode.NIGHT, 1800))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))

        # noinspection PyTypeChecker
        self.context = ExecutionContext(
            self.session,
            self.outbound_bus,
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

    def execute(self, measure: SensorMeasure):
        """
        Helper function that executes the command with given measure and then also executes
        all the commands that have been enqueued by the execution.
        """
        EvaluateMeasure(measure).execute(self.context)
        try:
            while True:
                self.context.command_queue.get_nowait().execute(self.context)
        except Empty:
            pass

    def test_device_not_available_with_no_entries(self):
        """
        Database is almost completely empty, there is no ping from device, which makes it
        unavailable. Nothing should happen.
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.HEATING,
                self.NOW - timedelta(minutes=1, seconds=0)
            )
        )

        self.execute(SensorMeasure(self.NOW, MeasureKind.LIVING_ROOM, 27.0, 55.0))
        self.assertEqual(0, self.outbound_bus.qsize())
        self.assertEqual(
            1,
            self.session.query(DeviceStatus).count(),
            'Status was off so not assumed off'
        )

    def test_device_not_available_but_last_status_is_on(self):
        """
        There is a PING from device, but it is too old which makes it unavailable. However, the AC status is set to ON.
        It should be reset back to OFF due to unavailability.
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DeviceStatus(
                DeviceKind.HEATING,
                self.NOW - timedelta(minutes=5),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=3, seconds=1)
            )
        )

        self.execute(SensorMeasure(self.NOW, MeasureKind.LIVING_ROOM, 27.0, 55.0))
        self.assertEqual(0, self.outbound_bus.qsize())

        logged_statuses = self.session.query(DeviceStatus).all()
        self.assertEqual(3, len(logged_statuses))
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5),
                PowerStatus.TURNED_ON
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            DeviceStatus(
                DeviceKind.HEATING,
                self.NOW - timedelta(minutes=5),
                PowerStatus.TURNED_OFF
            ),
            logged_statuses[1]
        )
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW,
                PowerStatus.TURNED_OFF
            ),
            logged_statuses[2]
        )

    def test_turn_off(self):
        """
        AC should be turned off
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 24.6))
        self.assertEqual(2, self.outbound_bus.qsize())
        self.assertEqual(self.TURN_OFF_BYTES, self.outbound_bus.get_nowait().encoded_data)
        self.assertEqual(self.TURN_OFF_BYTES, self.outbound_bus.get_nowait().encoded_data)

        logged_statuses = self.session.query(DeviceStatus).all()
        self.assertEqual(2, len(logged_statuses))
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_ON
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW,
                PowerStatus.TURNED_OFF
            ),
            logged_statuses[1]
        )

    def test_no_turn_off_temperature_in_range(self):
        """
        AC should not be turned off because temperature hasn't met threshold yet
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 24.8))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_no_turn_off_ac_in_grace_period(self):
        """
        AC should not be turned even though temperature has met threshold, because AC is in grace period
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=4, seconds=59),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 24.0))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_no_turn_off_already_turned_off(self):
        """
        AC should not be turned off because it's already in the OFF state
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=6, seconds=59),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=3),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 24.0))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_turn_on(self):
        """
        AC should be turned on
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=8, seconds=59), MeasureKind.LIVING_ROOM, 25.4))
        self.assertEqual(2, self.outbound_bus.qsize())
        self.assertEqual(self.TURN_ON_BYTES, self.outbound_bus.get_nowait().encoded_data)
        self.assertEqual(self.TURN_ON_BYTES, self.outbound_bus.get_nowait().encoded_data)

        logged_statuses = self.session.query(DeviceStatus).all()
        self.assertEqual(2, len(logged_statuses))
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_OFF
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW,
                PowerStatus.TURNED_ON
            ),
            logged_statuses[1]
        )

    def test_no_turn_on_measure_from_other_sensor_lower(self):
        """
        AC should be turned on
        """
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(SensorMeasure(self.NOW - timedelta(minutes=5, seconds=1), MeasureKind.BEDROOM, 25.3))
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=8, seconds=59), MeasureKind.LIVING_ROOM, 25.4))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_no_turn_on_temperature_in_range(self):
        """
        AC should not be turned on because temperature hasn't met threshold yet
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=1),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 25.2))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_no_turn_on_ac_in_grace_period(self):
        """
        AC should not be turned on even though temperature has met threshold, because AC is in grace period
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=4, seconds=59),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 26.0))
        self.assertEqual(0, self.outbound_bus.qsize())

    def test_no_turn_on_already_turned_on(self):
        """
        AC should not be turned on because it's already in the ON state
        """
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=6, seconds=59),
                PowerStatus.TURNED_OFF
            )
        )
        self.session.add(
            DeviceStatus(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=5, seconds=3),
                PowerStatus.TURNED_ON
            )
        )
        self.session.add(
            DevicePing(
                DeviceKind.COOLING,
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )

        self.execute(SensorMeasure(self.NOW - timedelta(minutes=9, seconds=59), MeasureKind.LIVING_ROOM, 26.0))
        self.assertEqual(0, self.outbound_bus.qsize())
