import logging
from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from command_bus.ExecutionContext import ExecutionContext
from persistence import AbstractBase, SensorMeasure, SensorMeasureRepository


class TestSensorMeasureRepository(TestCase):
    """
    Tests the sensor measure repository"
    """

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)
        logging.disable(logging.CRITICAL)

        self.session = Session(engine)
        self.mock_queue = Mock()

        # noinspection PyTypeChecker
        self.context = ExecutionContext(
            self.session,
            Mock(),
            self.mock_queue,
            Mock(),
            datetime,
        )

        self.repository = SensorMeasureRepository(self.session)

        def is_measure_eq(first: SensorMeasure, second: SensorMeasure, msg=None) -> None:
            self.assertEqual(first.timestamp, second.timestamp, msg)
            self.assertEqual(first.kind, second.kind, msg)
            self.assertEqual(first.temperature, second.temperature, msg)
            self.assertEqual(first.humidity, second.humidity, msg)
            self.assertEqual(first.voltage, second.voltage, msg)

        self.addTypeEqualityFunc(SensorMeasure, is_measure_eq)

    def test_no_measure_exists(self):
        """
        Confirms nothing is returned when there are no measures
        """
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.LIVING_ROOM))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.BEDROOM))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.OUTDOOR))

    def test_fetching_without_age_limit(self):
        """
        Confirms it returns expected results when querying for last temperature without age limit
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            SensorMeasure.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.LIVING_ROOM))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.BEDROOM))
        self.assertEqual(measure, self.repository.get_last_temperature(SensorMeasure.OUTDOOR))

    def test_fetching_with_age_limit_including_measure(self):
        """
        Confirms it returns expected results when querying for last temperature with an age limit
        that includes saved measure.
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            SensorMeasure.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        max_age = datetime(2023, 9, 13, 11, 34, 15)
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.LIVING_ROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.BEDROOM, max_age))
        self.assertEqual(measure, self.repository.get_last_temperature(SensorMeasure.OUTDOOR, max_age))

    def test_fetching_with_age_limit_excluding_measure(self):
        """
        Confirms it returns expected results when querying for last temperature with an age limit
        that does not include saved measure.
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            SensorMeasure.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        max_age = datetime(2023, 9, 13, 11, 35, 16)
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.LIVING_ROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.BEDROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(SensorMeasure.OUTDOOR, max_age))
