import asyncio
import websockets
from .types import PayloadTypes
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig()


class Client:
    def __init__(self, local_name, loop = None, port=13254):
        logger.setLevel(logging.DEBUG)
        self.uri = f"ws://localhost:{port}"        
        self.local_name = local_name
        self.websocket = None
        self.routes = {}
        
        self.loop = loop or asyncio.get_running_loop()
        self.authorized = False

    async def send_message(self, data):
        await self.websocket.send(json.dumps(data))
        
    async def start(self):
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(self.uri, close_timeout=0, ping_interval=None)
            logger.info("Connected to Websocket")
            await self.send_message({"type": PayloadTypes.verification, "id":self.local_name})
            logger.info("Verification request sent")
            self.loop.create_task(self.__on_message())
            logger.info("Listening to messages")
        else:
            raise ConnectionError("Websocket is already connected!")

    def route(self, name=None):
        def route_decorator(func):
            if (name is None and func.__name__ in self.routes) or (name is not None and name in self.routes):
                raise ValueError("Route name already exists!")
            
            self.routes[name or func.__name__] = func
            return func
            
        return route_decorator

    async def request(self, route, source, *args, **kwargs):
        if self.websocket is not None and self.websocket.open:
            await self.send_message(
                {"type": PayloadTypes.request,
                 "id":self.local_name,
                 "destination": source,
                 "route": route,
                 "args": args,
                 "kwargs": kwargs})


    
    async def __on_message(self):
        while True:
            response = json.loads(await self.websocket.recv())
            if response["type"] == PayloadTypes.success:
                logger.info("Authorized Successfully")
                self.authorized = True

            if response["type"] == PayloadTypes.request:
                if response["request"] not in self.routes:
                    logger.info("Failed to fulful request, route not found")
                    self.loop.create_task(self.send_message({"type":4, "details":"Route does not exist!"}))

            if response["type"] == PayloadTypes.error:
                logger.warning("Failed to fulful request, route not found")

            

                
