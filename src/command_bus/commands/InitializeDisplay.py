import asyncio
import json
from websockets.legacy.protocol import WebSocketCommonProtocol
from persistence import (
    AwayStatusRepository, SensorMeasureRepository, DevicePingRepository, ThresholdTemperatureRepository,
    DeviceStatusRepository, DeviceControlRepository,
)
from domain_types import DeviceKind, MeasureKind, OperatingMode, PowerStatus
from ui import (
    TemperatureUpdate, HumidityUpdate, DevicePingReceived, ThresholdTemperatureUpdate, DeviceStatusUpdate,
    DeviceControlUpdate, AwayStatusUpdate
)
from .AbstractCommand import AbstractCommand
from ..ExecutionContext import ExecutionContext


class InitializeDisplay(AbstractCommand):
    """
    A command that initialized a freshly-connected UI client
    """

    def __init__(self, websocket: WebSocketCommonProtocol):
        self.websocket = websocket

    def execute(self, context: ExecutionContext) -> None:
        """
        Send all the required data to the client.
        """
        asyncio.run(self.send_away_status(context))

        for measure_kind in MeasureKind:
            asyncio.run(self.send_measure(measure_kind, context))

        for device_kind in DeviceKind:
            asyncio.run(self.send_device_status(device_kind, context))

    async def send_away_status(self, context: ExecutionContext):
        """
        Send the away statis
        """
        away_status_repository = AwayStatusRepository(context.db_session)
        await self.websocket.send(json.dumps(AwayStatusUpdate(away_status_repository.is_away())))

    async def send_measure(self, kind: MeasureKind, context: ExecutionContext):
        """
        Send the data for given measure kind
        """
        measure = SensorMeasureRepository(context.db_session).get_last_temperature(kind)

        if measure is None:
            return

        await self.websocket.send(json.dumps(TemperatureUpdate(measure.timestamp, kind, measure.temperature)))
        if measure.humidity is None:
            return

        await self.websocket.send(json.dumps(HumidityUpdate(measure.timestamp, kind, measure.humidity)))

    async def send_device_status(self, kind: DeviceKind, context: ExecutionContext):
        """
        Sends the current status of given device kind
        """
        await self.websocket.send(
            json.dumps(
                DeviceControlUpdate(
                    kind,
                    DeviceControlRepository(context.db_session).get_measures_controlling(kind)
                )
            )
        )

        current_status = DeviceStatusRepository(context.db_session).get_current_status(kind)
        await self.websocket.send(
            json.dumps(
                DeviceStatusUpdate(kind, current_status == PowerStatus.TURNED_ON)
            )
        )

        threshold_temperature_repository = ThresholdTemperatureRepository(context.db_session)
        for mode in OperatingMode:
            await self.websocket.send(
                json.dumps(
                    ThresholdTemperatureUpdate(threshold_temperature_repository.get_threshold_temperature(kind, mode))
                )
            )

        last_ping = DevicePingRepository(context.db_session).get_last_ping(kind)
        if last_ping is not None:
            await self.websocket.send(json.dumps(DevicePingReceived(last_ping.kind, last_ping.timestamp)))
