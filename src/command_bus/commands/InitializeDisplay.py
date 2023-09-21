import asyncio
import json
from websockets.legacy.protocol import WebSocketCommonProtocol
from persistence import (
    AirConditionerStatus, SensorMeasure, SensorMeasureRepository, AirConditionerPingRepository,
    TargetTemperatureRepository, AirConditionerStatusLogRepository, SettingsRepository
)
from ui import TemperatureUpdate, HumidityUpdate, AcPing, TargetTemperatureUpdate, AcStatusUpdate, AcManagementUpdate
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
        asyncio.run(self.send_measure(SensorMeasure.OUTDOOR, context))
        asyncio.run(self.send_measure(SensorMeasure.LIVING_ROOM, context))
        asyncio.run(self.send_measure(SensorMeasure.BEDROOM, context))
        asyncio.run(self.send_ac_status(context))

    async def send_measure(self, kind: int, context: ExecutionContext):
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

    async def send_ac_status(self, context: ExecutionContext):
        """
        Sends the current status of the AC
        """
        await self.websocket.send(
            json.dumps(
                AcManagementUpdate(
                    SettingsRepository(context.db_session).get_settings().ac_management_enabled
                )
            )
        )

        await self.websocket.send(
            json.dumps(
                TargetTemperatureUpdate(
                    TargetTemperatureRepository(context.db_session).get_target_temperature().temperature
                )
            )
        )

        current_status = AirConditionerStatusLogRepository(context.db_session).get_current_status()
        await self.websocket.send(
            json.dumps(
                AcStatusUpdate(current_status == AirConditionerStatus.TURNED_ON)
            )
        )

        last_ping = AirConditionerPingRepository(context.db_session).get_last_ping()
        if last_ping is not None:
            await self.websocket.send(json.dumps(AcPing(last_ping.timestamp)))
