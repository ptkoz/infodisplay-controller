from datetime import datetime, timedelta
from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from persistence import AbstractBase, SensorMeasure, SensorMeasureRepository
from domain_types import MeasureKind


class TestSensorMeasureRepository(TestCase):
    """
    Tests the sensor measure repository
    """

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)

        self.session = Session(engine)
        self.repository = SensorMeasureRepository(self.session)

        def is_measure_eq(first: SensorMeasure, second: SensorMeasure, msg=None) -> None:
            self.assertEqual(first.timestamp, second.timestamp, msg)
            self.assertEqual(first.kind, second.kind, msg)
            self.assertEqual(first.temperature, second.temperature, msg)
            self.assertEqual(first.humidity, second.humidity, msg)
            self.assertEqual(first.voltage, second.voltage, msg)

        self.addTypeEqualityFunc(SensorMeasure, is_measure_eq)

    def tearDown(self) -> None:
        self.session.close()

    def test_no_measure_exists(self):
        """
        Confirms nothing is returned when there are no measures
        """
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.LIVING_ROOM))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.BEDROOM))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.OUTDOOR))

    def test_fetching_without_age_limit(self):
        """
        Confirms it returns expected results when querying for last temperature without age limit
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            MeasureKind.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.LIVING_ROOM))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.BEDROOM))
        self.assertEqual(measure, self.repository.get_last_temperature(MeasureKind.OUTDOOR))

    def test_fetching_with_age_limit_including_measure(self):
        """
        Confirms it returns expected results when querying for last temperature with an age limit
        that includes saved measure.
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            MeasureKind.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        max_age = datetime(2023, 9, 13, 11, 34, 15)
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.LIVING_ROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.BEDROOM, max_age))
        self.assertEqual(measure, self.repository.get_last_temperature(MeasureKind.OUTDOOR, max_age))

    def test_fetching_with_age_limit_excluding_measure(self):
        """
        Confirms it returns expected results when querying for last temperature with an age limit
        that does not include saved measure.
        """
        measure = SensorMeasure(
            datetime(2023, 9, 13, 11, 35, 15),
            MeasureKind.OUTDOOR,
            22.01,
            56.5,
            5.0,
        )
        self.session.add(measure)

        max_age = datetime(2023, 9, 13, 11, 35, 16)
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.LIVING_ROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.BEDROOM, max_age))
        self.assertIsNone(self.repository.get_last_temperature(MeasureKind.OUTDOOR, max_age))

    def test_fetching_last_min(self):
        """
        Confirms it returns expected results when querying for last temperature of given min value
        """
        base_time = datetime(2023, 9, 13, 11, 35, 15)

        self.session.add(SensorMeasure(base_time - timedelta(minutes=5), MeasureKind.OUTDOOR, 20.03))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=4), MeasureKind.OUTDOOR, 20.02))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=3), MeasureKind.OUTDOOR, 20.01))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=1), MeasureKind.OUTDOOR, 19.99))

        self.assertEqual(
            20.01,
            self.repository.get_last_min(MeasureKind.OUTDOOR, 20.00).temperature
        )

    def test_fetching_last_max(self):
        """
        Confirms it returns expected results when querying for last temperature of given max value
        """
        base_time = datetime(2023, 9, 13, 11, 35, 15)

        self.session.add(SensorMeasure(base_time - timedelta(minutes=5), MeasureKind.OUTDOOR, 19.97))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=4), MeasureKind.OUTDOOR, 19.98))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=3), MeasureKind.OUTDOOR, 19.99))
        self.session.add(SensorMeasure(base_time - timedelta(minutes=1), MeasureKind.OUTDOOR, 20.01))

        self.assertEqual(
            19.99,
            self.repository.get_last_max(MeasureKind.OUTDOOR, 20.00).temperature
        )
