from datetime import datetime
from typing import List, Tuple, Type
from domain_types import DeviceKind, MeasureKind
from ._AbstractRepository import AbstractRepository
from .AwayStatusRepository import AwayStatusRepository
from .DeviceControlRepository import DeviceControlRepository
from .ThresholdTemperatureRepository import ThresholdTemperatureRepository


class TemperatureRegulationRepository(AbstractRepository):
    """
    Repository for managing controller settings
    """
    # measure kinds that are subject to anti-freeze protection
    __ANTI_FREEZE_MEASURES = [MeasureKind.LIVING_ROOM, MeasureKind.BEDROOM]
    # temperature below which the anti-freeze protection in away mode will start heating
    __ANTI_FREEZE_TEMP: float = 15.0

    def get_regulation_for_measure(self, measure: MeasureKind, time: Type[datetime]) -> List[Tuple[DeviceKind, float]]:
        """
        Returns a list of devices that use given measure to regulate temperature and the threshold temperature set.
        """
        away_repository = AwayStatusRepository(self._session)
        if away_repository.is_away():
            # In away mode we just make sure temperature in every room does not drop below 15C
            if measure not in self.__ANTI_FREEZE_MEASURES:
                return []

            return [(DeviceKind.HEATING, self.__ANTI_FREEZE_TEMP)]

        device_control_repository = DeviceControlRepository(self._session)
        threshold_temperature_repository = ThresholdTemperatureRepository(self._session)
        operating_mode = device_control_repository.get_mode_for(time.now())

        return [
            (
                device.device_kind,
                threshold_temperature_repository.get_threshold_temperature(device.device_kind, operating_mode)
                    .temperature
            ) for device in device_control_repository.get_devices_controlled_by(measure, operating_mode)
        ]

    def get_regulation_for_device(self, device: DeviceKind, time: Type[datetime]) -> List[Tuple[MeasureKind, float]]:
        """
        Returns a list of measures that affect given device and the threshold temperature set.
        """
        away_repository = AwayStatusRepository(self._session)
        if away_repository.is_away():
            # In away mode we just make sure temperature in every room does not drop below 15C
            if device != DeviceKind.HEATING:
                # We only need heater to accomplish that
                return []

            return [
                (measure_kind, self.__ANTI_FREEZE_TEMP) for measure_kind in self.__ANTI_FREEZE_MEASURES
            ]

        device_control_repository = DeviceControlRepository(self._session)
        threshold_temperature_repository = ThresholdTemperatureRepository(self._session)
        operating_mode = device_control_repository.get_mode_for(time.now())

        return [
            (
                measure.measure_kind,
                threshold_temperature_repository.get_threshold_temperature(device, operating_mode).temperature
            ) for measure in device_control_repository.get_measures_controlling(device, operating_mode)
        ]
