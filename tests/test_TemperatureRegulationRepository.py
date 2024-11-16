from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus
from persistence import AbstractBase, AwayStatus, DeviceControl, ThresholdTemperature, TemperatureRegulationRepository


class TestTemperatureRegulationRepository(TestCase):
    """
    Tests for temperature regulation repository
    """
    DAY = datetime(2023, 9, 13, 11, 35, 15)
    NIGHT = datetime(2023, 9, 13, 3, 0, 15)
    FRIDAY_7AM = datetime(2024, 10, 18, 7, 0, 0)
    SATURDAY_7AM = datetime(2024, 10, 19, 7, 0, 0)

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)

        self.time_source = Mock()

        self.session = Session(engine)
        self.repository = TemperatureRegulationRepository(self.session)

    def test_empty_database(self):
        """
        Tests whether correct results are returned when database is empty
        """
        for now in [self.DAY, self.NIGHT]:
            self.time_source.now = Mock(return_value=now)
            for kind in MeasureKind:
                self.assertListEqual([], self.repository.get_regulation_for_measure(kind, self.time_source))

            for kind in DeviceKind:
                self.assertListEqual([], self.repository.get_regulation_for_device(kind, self.time_source))

    def test_empty_database_in_away_mode(self):
        """
        In away mode no regulations are needed, anti-freeze is always returned
        """
        self.session.add(AwayStatus(datetime(2023, 9, 9, 11, 00, 00), PowerStatus.TURNED_ON))

        for now in [self.DAY, self.NIGHT]:
            self.time_source.now = Mock(return_value=now)
            self.assertListEqual(
                [],
                [
                    (r[0], r[1].temperature) for r in
                    self.repository.get_regulation_for_measure(MeasureKind.OUTDOOR, self.time_source)
                ]
            )

            self.assertListEqual(
                [(DeviceKind.HEATING, 15)],
                [
                    (r[0], r[1].temperature) for r in
                    self.repository.get_regulation_for_measure(MeasureKind.LIVING_ROOM, self.time_source)
                ]
            )

            self.assertListEqual(
                [(DeviceKind.HEATING, 15)],
                [
                    (r[0], r[1].temperature) for r in
                    self.repository.get_regulation_for_measure(MeasureKind.BEDROOM, self.time_source)
                ]
            )

    def setup_data(self):
        """
        Setup test data in the database
        """
        # hence to target temperature for cooling at night, default should be used
        self.session.add(ThresholdTemperature(DeviceKind.HEATING, OperatingMode.DAY, 2150))
        self.session.add(ThresholdTemperature(DeviceKind.HEATING, OperatingMode.NIGHT, 1900))
        self.session.add(ThresholdTemperature(DeviceKind.COOLING, OperatingMode.DAY, 2350))

        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.NIGHT))

    def data_getting_for_measure(self):
        """
        Data provider for test_getting_for_measure
        """
        return [
            (self.DAY, MeasureKind.OUTDOOR, []),
            (self.NIGHT, MeasureKind.OUTDOOR, []),
            (self.DAY, MeasureKind.LIVING_ROOM, [
                (DeviceKind.HEATING, 21.5),
                (DeviceKind.COOLING, 23.5)
            ]),
            (self.NIGHT, MeasureKind.LIVING_ROOM, [
                (DeviceKind.COOLING, 26)
            ]),
            (self.DAY, MeasureKind.BEDROOM, [
                (DeviceKind.HEATING, 21.5)
            ]),
            (self.NIGHT, MeasureKind.BEDROOM, [
                (DeviceKind.HEATING, 19)
            ]),
            # Friday 7am should be considered day
            (self.FRIDAY_7AM, MeasureKind.BEDROOM, [
                (DeviceKind.HEATING, 21.5)
            ]),
            # Saturday 7am should be considered night
            (self.SATURDAY_7AM, MeasureKind.BEDROOM, [
                (DeviceKind.HEATING, 19)
            ]),
        ]

    def test_getting_for_measure(self):
        """
        Test whether getting regulations for measure work as expected
        """
        self.setup_data()
        for (now, measure, expected) in self.data_getting_for_measure():
            self.time_source.now = Mock(return_value=now)
            regulations = self.repository.get_regulation_for_measure(measure, self.time_source)
            self.assertListEqual(
                expected,
                [(r[0], r[1].temperature) for r in regulations]
            )

    def data_getting_for_device(self):
        """
        Data provider for test_getting_for_device
        """
        return [
            (self.DAY, DeviceKind.COOLING, [
                (MeasureKind.LIVING_ROOM, 23.5)
            ]),
            (self.NIGHT, DeviceKind.COOLING, [
                (MeasureKind.LIVING_ROOM, 26.0)
            ]),
            (self.DAY, DeviceKind.HEATING, [
                (MeasureKind.BEDROOM, 21.5),
                (MeasureKind.LIVING_ROOM, 21.5)
            ]),
            (self.NIGHT, DeviceKind.HEATING, [
                (MeasureKind.BEDROOM, 19)
            ]),
        ]

    def test_getting_for_device(self):
        """
        Test whether getting regulations for device work as expected
        """
        self.setup_data()
        for (now, device, expected) in self.data_getting_for_device():
            self.time_source.now = Mock(return_value=now)
            regulations = self.repository.get_regulation_for_device(device, self.time_source)
            self.assertListEqual(
                expected,
                [(r[0], r[1].temperature) for r in regulations]
            )
