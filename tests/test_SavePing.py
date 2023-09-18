import logging
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus import SavePing
from command_bus.ExecutionContext import ExecutionContext
from persistence import AbstractBase, AirConditionerPing


class TestSavePing(TestCase):
    """
    Test case for saving a PING
    """
    NOW = datetime(2023, 9, 13, 11, 35, 15)

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)
        logging.disable(logging.CRITICAL)

        self.mock_datetime = Mock()
        self.mock_datetime.now = Mock(return_value=self.NOW)
        self.session = Session(engine)
        self.mock_queue = Mock()

        # noinspection PyTypeChecker
        self.context = ExecutionContext(
            self.session,
            Mock(),
            self.mock_queue,
            self.mock_datetime,
        )

        self.command = SavePing(self.NOW)

        def is_ping_eq(first, second, msg=None) -> None:
            self.assertEqual(first.timestamp, second.timestamp, 'Failed asserting timestamp is the same')

        self.addTypeEqualityFunc(AirConditionerPing, is_ping_eq)

    def test_saving_next_ping(self):
        """
        Given that pings are arriving as usual, every minute, this should just save the next ping
        """
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=3)))
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=2)))
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=1)))

        self.command.execute(self.context)

        self.mock_queue.put_nowait.assert_not_called()

        pings = self.session.query(AirConditionerPing).all()
        self.assertEqual(4, len(pings))
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=3)), pings[0])
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=2)), pings[1])
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=1)), pings[2])
        self.assertEqual(AirConditionerPing(self.NOW), pings[3])

    def test_saving_after_inactive_period(self):
        """
        Given that there were no pings for some time, this ping should evaluate air conditioning
        as we assume AC has just went back online
        """
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=5, seconds=3)))
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=4, seconds=2)))
        self.session.add(AirConditionerPing(self.NOW - timedelta(minutes=3, seconds=1)))

        self.command.execute(self.context)

        self.mock_queue.put_nowait.assert_called_once()

        pings = self.session.query(AirConditionerPing).all()
        self.assertEqual(4, len(pings))
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=5, seconds=3)), pings[0])
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=4, seconds=2)), pings[1])
        self.assertEqual(AirConditionerPing(self.NOW - timedelta(minutes=3, seconds=1)), pings[2])
        self.assertEqual(AirConditionerPing(self.NOW), pings[3])
