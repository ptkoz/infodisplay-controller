from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from domain_types import DeviceKind, MeasureKind, OperatingMode
from persistence import AbstractBase, DeviceControl, DeviceControlRepository


def device_control_repr(self: DeviceControl):
    """
    Provides nice representation of DeviceControl
    """
    return f"DeviceControl(device={self.device_kind:#x},measure={self.measure_kind:#x},mode={self.operating_mode.name})"


DeviceControl.__repr__ = device_control_repr # type: ignore


class TestDeviceControlRepository(TestCase):
    """
    Tests the device controlling repository
    """

    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        AbstractBase.metadata.create_all(engine)

        self.session = Session(engine)
        self.repository = DeviceControlRepository(self.session)

        def is_device_control_eq(first: DeviceControl, second: DeviceControl, msg=None) -> None:
            self.assertEqual(first.device_kind, second.device_kind, msg)
            self.assertEqual(first.measure_kind, second.measure_kind, msg)
            self.assertEqual(first.operating_mode, second.operating_mode, msg)

        self.addTypeEqualityFunc(DeviceControl, is_device_control_eq)

    def tearDown(self) -> None:
        self.session.close()

    def test_empty_database(self):
        """
        Confirms nothing is returned when database is empty
        """
        for kind in MeasureKind:
            for mode in OperatingMode:
                self.assertListEqual([], self.repository.get_devices_controlled_by(kind, mode))

        for kind in DeviceKind:
            self.assertListEqual([], self.repository.get_measures_controlling(kind))
            for mode in OperatingMode:
                self.assertListEqual([], self.repository.get_measures_controlling(kind, mode))

    def test_obtaining_controlled_devices(self):
        """
        Confirms that obtaining controlled devices works as expected
        """
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))

        outdoor_day = self.repository.get_devices_controlled_by(MeasureKind.OUTDOOR, OperatingMode.DAY)
        outdoor_night = self.repository.get_devices_controlled_by(MeasureKind.OUTDOOR, OperatingMode.NIGHT)
        living_room_day = self.repository.get_devices_controlled_by(MeasureKind.LIVING_ROOM, OperatingMode.DAY)
        living_room_night = self.repository.get_devices_controlled_by(MeasureKind.LIVING_ROOM, OperatingMode.NIGHT)
        bedroom_day = self.repository.get_devices_controlled_by(MeasureKind.BEDROOM, OperatingMode.DAY)
        bedroom_night = self.repository.get_devices_controlled_by(MeasureKind.BEDROOM, OperatingMode.NIGHT)

        self.assertEqual(0, len(outdoor_day))
        self.assertEqual(0, len(outdoor_night))
        self.assertEqual(2, len(living_room_day))
        self.assertEqual(0, len(living_room_night))
        self.assertEqual(1, len(bedroom_day))
        self.assertEqual(1, len(bedroom_night))

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            living_room_day[0]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            living_room_day[1]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY),
            bedroom_day[0]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT),
            bedroom_night[0]
        )

    def test_obtaining_controlling_measures(self):
        """
        Conforms that obtaining controlling measures works as expected
        """
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))

        heating = self.repository.get_measures_controlling(DeviceKind.HEATING)
        cooling = self.repository.get_measures_controlling(DeviceKind.COOLING)

        self.assertEqual(3, len(heating))
        self.assertEqual(1, len(cooling))

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT),
            heating[0]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY),
            heating[1]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            heating[2]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            cooling[0]
        )

    def test_obtaining_controlling_measures_day_only(self):
        """
        Conforms that obtaining controlling measures for day mode works as expected
        """
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))

        heating_day = self.repository.get_measures_controlling(DeviceKind.HEATING, OperatingMode.DAY)
        cooling_day = self.repository.get_measures_controlling(DeviceKind.COOLING, OperatingMode.DAY)

        self.assertEqual(2, len(heating_day))
        self.assertEqual(1, len(cooling_day))

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY),
            heating_day[0]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            heating_day[1]
        )

        self.assertEqual(
            DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY),
            cooling_day[0]
        )

    def test_obtaining_controlling_measures_night_only(self):
        """
        Conforms that obtaining controlling measures for night mode works as expected
        """
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.HEATING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))
        self.session.add(DeviceControl(DeviceKind.COOLING, MeasureKind.LIVING_ROOM, OperatingMode.DAY))

        heating_night = self.repository.get_measures_controlling(DeviceKind.HEATING, OperatingMode.NIGHT)
        cooling_night = self.repository.get_measures_controlling(DeviceKind.COOLING, OperatingMode.NIGHT)

        self.assertEqual(1, len(heating_night))
        self.assertEqual(0, len(cooling_night))

        self.assertEqual(
            DeviceControl(DeviceKind.HEATING, MeasureKind.BEDROOM, OperatingMode.NIGHT),
            heating_night[0]
        )
