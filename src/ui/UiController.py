import json
import logging
import asyncio
from queue import Queue
from threading import Event
from typing import List
import websockets.server
from websockets.legacy.protocol import broadcast, WebSocketCommonProtocol


class UiController:
    """
    Controls communication with the UI
    """

    def __init__(self, port: int, command_bus: Queue, stop: Event):
        self.port = port
        self.command_bus = command_bus
        self.stop = stop
        self.listeners: List = []

    def publish(self, message: dict):
        """
        Publish information to all connected customers
        """
        broadcast(self.listeners, json.dumps(message))

    async def handle_new_listener(self, websocket: WebSocketCommonProtocol):
        """
        Handles a new listener joining the controller.
        """
        self.listeners.append(websocket)
        logging.debug("New consumer joined, number of consumers %d", len(self.listeners))

        from command_bus import InitializeDisplay
        self.command_bus.put_nowait(InitializeDisplay(websocket))

        async for message in websocket:
            from command_bus import UpdateConfiguration
            self.command_bus.put_nowait(UpdateConfiguration(json.loads(message)))

        self.listeners.remove(websocket)
        logging.debug("Consumer dropped, number of consumers %d", len(self.listeners))

    async def start_server(self):
        """
        Starts the websocket server that handles UI clients.
        """
        async with websockets.server.serve(self.handle_new_listener, "", self.port):
            while not self.stop.is_set():
                await asyncio.sleep(5)

    def run(self):
        """
        Run the UI controller
        """
        asyncio.run(self.start_server())
