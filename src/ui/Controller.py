import json
import logging
import asyncio
from threading import Event
import websockets


class Controller:
    """
    Controls communication with the UI
    """

    def __init__(self, port: int, stop: Event):
        self.port = port
        self.stop = stop
        self.listeners = []

    def publish(self, message: dict):
        """
        Publish information to all connected customers
        """
        websockets.broadcast(self.listeners, json.dumps(message))

    async def handle_new_listener(self, websocket):
        """
        Handles a new listener joining the controller.
        """
        self.listeners.append(websocket)
        logging.debug("New consumer joined, number of consumers %d", len(self.listeners))
        async for message in websocket:
            logging.debug(message)
        self.listeners.remove(websocket)
        logging.debug("Consumer dropped, number of consumers %d", len(self.listeners))

    async def start_server(self):
        """
        Starts the websocket server that handles UI clients.
        """
        async with websockets.serve(self.handle_new_listener, "", self.port):
            while not self.stop.is_set():
                await asyncio.sleep(5)

    def run(self):
        """
        Run the UI controller
        """
        asyncio.run(self.start_server())
