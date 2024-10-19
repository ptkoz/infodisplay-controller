from datetime import datetime
from typing import List, Optional
from domain_types import DeviceKind, MeasureKind, OperatingMode
from persistence.models import DeviceControl
from ._AbstractRepository import AbstractRepository


class DeviceControlRepository(AbstractRepository):
    """
    Repository for managing controller settings
    """

    def set_controlling_measures(self, device_kind: DeviceKind, mode: OperatingMode, measures: List[MeasureKind]):
        """
        Sets measures that will control given device in given mode.
        """
        for device_control in self.get_measures_controlling(device_kind, mode):
            self._session.delete(device_control)

        for measure_kind in measures:
            self._session.add(DeviceControl(device_kind, measure_kind, mode))

    def get_measures_controlling(
        self,
        device_kind: DeviceKind,
        mode: Optional[OperatingMode] = None
    ) -> List[DeviceControl]:
        """
        Returns a list of measures thar are controlling given device kind, optionally narrowed down
        to given operating mode
        """
        query = self._session.query(DeviceControl).filter(DeviceControl.device_kind == device_kind)

        if mode is not None:
            query = query.filter(DeviceControl.operating_mode == mode)

        return query.all()

    def get_devices_controlled_by(
        self,
        measure_kind: MeasureKind,
        mode: OperatingMode
    ) -> List[DeviceControl]:
        """
        Returns a list of devices thar are controlled by given measure kind in given operating mode
        """
        return (
            self
            ._session
            .query(DeviceControl)
            .filter(DeviceControl.measure_kind == measure_kind)
            .filter(DeviceControl.operating_mode == mode)
            .order_by(DeviceControl.id)
            .all()
        )

    def get_mode_for(self, timestamp: datetime) -> OperatingMode:
        """
        Returns the mode that is active at given time
        """
        day_start_hour = 6
        day_end_hour = 22

        if timestamp.weekday() >= 5:
            # weekend
            day_start_hour = 8
            day_end_hour = 22

        if day_start_hour <= timestamp.hour < day_end_hour:
            return OperatingMode.DAY

        return OperatingMode.NIGHT
