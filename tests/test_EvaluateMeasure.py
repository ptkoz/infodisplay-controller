import logging
from datetime import datetime, timedelta
from queue import Empty, Queue
from unittest import TestCase
from unittest.mock import call, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus import EvaluateMeasure
from command_bus.ExecutionContext import ExecutionContext
from persistence import AbstractBase, DeviceControl, DevicePing, DeviceStatus, SensorMeasure, TargetTemperature
from radio_bus import Radio
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus


class TestEvaluateMeasure(TestCase):
    """
    Test case for air conditioning evaluation
    """
    NOW = datetime(2023, 9, 13, 11, 35, 15)
    TURN_ON_BYTES = b'\xFF\x03\x8A\x02\x01'
    TURN_OFF_BYTES = b'\xFF\x03\x8A\x02\x02'

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)
        logging.disable(logging.CRITICAL)

        class StubRadio(Radio):
            """
            A stub radio implementation with mocked serial
            """

            # noinspection PyMissingConstructor
            def __init__(self):  # pylint: disable=W0231
                self.serial = Mock()

        self.radio = StubRadio()
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
            self.radio,
            Queue(),
            Mock(),
            self.mock_datetime,
        )

        def is_status_log_eq(first, second, msg=None) -> None:
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
        self.radio.serial.write.assert_not_called()
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
        self.radio.serial.write.assert_not_called()

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

        self.radio.serial.assert_has_calls(
            [
                call.write(self.TURN_OFF_BYTES),
                call.write(self.TURN_OFF_BYTES),
            ]
        )

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
        self.radio.serial.write.assert_not_called()

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
        self.radio.serial.write.assert_not_called()

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
        self.radio.serial.write.assert_not_called()

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
        self.radio.serial.assert_has_calls(
            [
                call.write(self.TURN_ON_BYTES),
                call.write(self.TURN_ON_BYTES),
            ]
        )

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
        self.radio.serial.write.assert_not_called()

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
        self.radio.serial.write.assert_not_called()

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
        self.radio.serial.write.assert_not_called()
