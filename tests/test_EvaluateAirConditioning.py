import logging
from datetime import datetime, timedelta
from queue import Queue
from unittest import TestCase
from unittest.mock import call, Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus import EvaluateAirConditioning
from command_bus.ExecutionContext import ExecutionContext
from persistence import (
    AbstractBase, AirConditionerPing, AirConditionerStatus, AirConditionerStatusLog, SensorMeasure,
    Settings, TargetTemperature,
)
from radio_bus import Radio


class TestEvaluateAirConditioning(TestCase):
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
            # noinspection PyMissingConstructor
            def __init__(self):
                self.serial = Mock()

        self.radio = StubRadio()
        self.mock_datetime = Mock()
        self.mock_datetime.now = Mock(return_value=self.NOW)
        self.session = Session(engine)

        self.session.add(TargetTemperature(1, 2500))
        self.session.add(Settings(True))

        # noinspection PyTypeChecker
        self.context = ExecutionContext(
            self.session,
            self.radio,
            Queue(),
            self.mock_datetime,
        )

        self.command = EvaluateAirConditioning()

        def is_status_log_eq(first, second, msg=None) -> None:
            self.assertEqual(first.status, second.status, 'Failed asserting status is the same')
            self.assertEqual(first.timestamp, second.timestamp, 'Failed asserting timestamp is the same')

        self.addTypeEqualityFunc(AirConditionerStatusLog, is_status_log_eq)

    def tearDown(self) -> None:
        self.context.db_session.close()

    def test_air_conditioning_not_available_with_no_entries(self):
        """
        Database is almost completely empty, there is no ping from AC, which makes it
        unavailable. Nothing should happen.
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5),
                AirConditionerStatus.TURNED_OFF
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()
        self.assertEqual(
            1,
            self.session.query(AirConditionerStatusLog).count(),
            'Status was off so not assumed off'
        )

    def test_air_conditioning_not_available_but_last_status_is_on(self):
        """
        There is a PING from AC, but it is too old which makes it unavailable. However, the AC status is set to ON.
        It should be reset back to OFF due to unavailability.
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=3, seconds=1)
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

        logged_statuses = self.session.query(AirConditionerStatusLog).all()
        self.assertEqual(2, len(logged_statuses))
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5),
                AirConditionerStatus.TURNED_ON
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW,
                AirConditionerStatus.TURNED_OFF
            ),
            logged_statuses[1]
        )

    def test_no_temperature_measure(self):
        """
        AC is available and turned on, but there is no recent temperature measure that we could evaluate against.
        Nothing should happen
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=10, seconds=1),
                SensorMeasure.LIVING_ROOM,
                24.6
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=2),
                SensorMeasure.BEDROOM,
                23
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=1),
                SensorMeasure.OUTDOOR,
                21
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

        logged_statuses = self.session.query(AirConditionerStatusLog).all()
        self.assertEqual(1, len(logged_statuses))
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5),
                AirConditionerStatus.TURNED_ON
            ),
            logged_statuses[0]
        )

    def test_turn_off(self):
        """
        AC should be turned off
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                24.6
            )
        )

        self.command.execute(self.context)
        self.radio.serial.assert_has_calls(
            [
                call.write(self.TURN_OFF_BYTES),
                call.write(self.TURN_OFF_BYTES),
            ]
        )

        logged_statuses = self.session.query(AirConditionerStatusLog).all()
        self.assertEqual(2, len(logged_statuses))
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_ON
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW,
                AirConditionerStatus.TURNED_OFF
            ),
            logged_statuses[1]
        )

    def test_turn_off_management_disabled(self):
        """
        When AC is turned on, but AC management is disabled, we should turn it off even though
        criteria for turning off are not met yet.
        """
        self.session.query(Settings).first().ac_management_enabled = False
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=25),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(seconds=5)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(seconds=59),
                SensorMeasure.LIVING_ROOM,
                100
            )
        )

        self.command.execute(self.context)
        self.radio.serial.assert_has_calls(
            [
                call.write(self.TURN_OFF_BYTES),
                call.write(self.TURN_OFF_BYTES),
            ]
        )

    def test_no_turn_off_temperature_in_range(self):
        """
        AC should not be turned off because temperature hasn't met threshold yet
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                24.8
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_no_turn_off_ac_in_grace_period(self):
        """
        AC should not be turned even though temperature has met threshold, because AC is in grace period
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=4, seconds=59),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                24.0
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_no_turn_off_already_turned_off(self):
        """
        AC should not be turned off because it's already in the OFF state
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=6, seconds=59),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=3),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                24.0
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_turn_on(self):
        """
        AC should be turned on
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                25.0
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=8, seconds=59),
                SensorMeasure.LIVING_ROOM,
                25.4
            )
        )

        self.command.execute(self.context)
        self.radio.serial.assert_has_calls(
            [
                call.write(self.TURN_ON_BYTES),
                call.write(self.TURN_ON_BYTES),
            ]
        )

        logged_statuses = self.session.query(AirConditionerStatusLog).all()
        self.assertEqual(2, len(logged_statuses))
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_OFF
            ),
            logged_statuses[0]
        )
        self.assertEqual(
            AirConditionerStatusLog(
                self.NOW,
                AirConditionerStatus.TURNED_ON
            ),
            logged_statuses[1]
        )

    def test_no_turn_on_when_management_disabled(self):
        """
        AC should not be turned on even though all conditions are met, because
        ac management is disabled.
        """
        self.session.query(Settings).first().ac_management_enabled = False
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=25),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=1)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=2),
                SensorMeasure.LIVING_ROOM,
                100
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_no_turn_on_temperature_in_range(self):
        """
        AC should not be turned on because temperature hasn't met threshold yet
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=1),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                25.2
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_no_turn_on_ac_in_grace_period(self):
        """
        AC should not be turned on even though temperature has met threshold, because AC is in grace period
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=4, seconds=59),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                26.0
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()

    def test_no_turn_on_already_turned_on(self):
        """
        AC should not be turned on because it's already in the ON state
        """
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=6, seconds=59),
                AirConditionerStatus.TURNED_OFF
            )
        )
        self.session.add(
            AirConditionerStatusLog(
                self.NOW - timedelta(minutes=5, seconds=3),
                AirConditionerStatus.TURNED_ON
            )
        )
        self.session.add(
            AirConditionerPing(
                self.NOW - timedelta(minutes=2, seconds=59)
            )
        )
        self.session.add(
            SensorMeasure(
                self.NOW - timedelta(minutes=9, seconds=59),
                SensorMeasure.LIVING_ROOM,
                26.0
            )
        )

        self.command.execute(self.context)
        self.radio.serial.write.assert_not_called()
