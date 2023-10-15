from datetime import datetime, timedelta
from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from domain_types import PowerStatus
from persistence import AbstractBase, AwayStatusRepository


class TestAwayStatusRepository(TestCase):
    """
    Tests the Away Status repository
    """
    NOW = datetime(2023, 9, 13, 11, 35, 15)

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)

        self.session = Session(engine)
        self.repository = AwayStatusRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()

    def test_set_away_status(self):
        """
        Ensure setting away status work as expected
        """
        self.assertFalse(self.repository.is_away())

        self.repository.set_away_status(self.NOW - timedelta(minutes=5), PowerStatus.TURNED_OFF)
        self.repository.set_away_status(self.NOW - timedelta(minutes=10), PowerStatus.TURNED_ON)

        self.assertFalse(self.repository.is_away())

        self.repository.set_away_status(self.NOW - timedelta(minutes=4), PowerStatus.TURNED_ON)

        self.assertTrue(self.repository.is_away())
