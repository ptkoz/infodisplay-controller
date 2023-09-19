import asyncio
import json
from datetime import timedelta
from websockets.legacy.protocol import WebSocketCommonProtocol
from persistence import SensorMeasure, SensorMeasureRepository
from ui import TemperatureUpdate, HumidityUpdate
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
        asyncio.run(self.send(SensorMeasure.OUTDOOR, context))
        asyncio.run(self.send(SensorMeasure.LIVING_ROOM, context))
        asyncio.run(self.send(SensorMeasure.BEDROOM, context))

    async def send(self, kind: int, context: ExecutionContext):
        """
        Send the data for given measure kind
        """
        measure = (
            SensorMeasureRepository(context.db_session)
            .get_last_temperature(kind, context.time_source.now() - timedelta(minutes=60))
        )

        if measure is None:
            return

        await self.websocket.send(json.dumps(TemperatureUpdate(measure.timestamp, kind, measure.temperature)))
        if measure.humidity is None:
            return

        await self.websocket.send(json.dumps(HumidityUpdate(measure.timestamp, kind, measure.humidity)))
