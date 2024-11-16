import logging
from datetime import timedelta
from typing import List, Tuple
from domain_types import DeviceKind
from persistence import SensorMeasure, TemperatureRegulationRepository, SensorMeasureRepository, ThresholdTemperature
from .AbstractCommand import AbstractCommand
from .RegulateTemperature import RegulateTemperature
from ..ExecutionContext import ExecutionContext


class EvaluateDevice(AbstractCommand):
    """
    A command that queues device evaluation for all measures that are controlling given device
    """

    def __init__(self, kind: DeviceKind):
        self.kind = kind

    def execute(self, context: ExecutionContext) -> None:
        """
        Execute the command
        """
        measure_repository = SensorMeasureRepository(context.db_session)
        regulations = (
            TemperatureRegulationRepository(context.db_session)
            .get_regulation_for_device(self.kind, context.time_source)
        )

        if len(regulations) == 0:
            # This device is currently not regulated. Make sure it is switched off.
            from persistence import DevicePingRepository, DeviceStatusRepository, NounceRepository
            from devices import get_device_for_kind

            device = get_device_for_kind(
                self.kind,
                DevicePingRepository(context.db_session),
                DeviceStatusRepository(context.db_session),
                NounceRepository(context.db_session),
                context.time_source,
                context.publisher,
                context.outbound_bus
            )

            if device.is_turned_on():
                logging.info("Device %s is ON, but it is unregulated - attempting TURN OFF", self.kind.name)
                if device.can_turn_off():
                    device.turn_off()
                    logging.info('Device %s TURNED OFF successfully', self.kind.name)
                else:
                    logging.info('TURN OFF of device %s failed - device is in grace period', self.kind.name)

            return

        measures: List[Tuple[SensorMeasure, ThresholdTemperature]] = []
        for (measure_kind, threshold_temperature) in regulations:
            measure = measure_repository.get_last_temperature(
                measure_kind,
                context.time_source.now() - timedelta(minutes=10)
            )

            if measure is not None:
                measures.append((measure, threshold_temperature))

        # If there are multiple measures controlling single device, only consider the one with the lowest reading
        if len(measures) > 0:
            (measure, threshold_temperature) = min(measures, key=lambda x: x[0].temperature)
            context.command_queue.put_nowait(
                RegulateTemperature(self.kind, measure, threshold_temperature)
            )
