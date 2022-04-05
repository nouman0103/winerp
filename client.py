import asyncio
import websockets
import json
import logging
from .lib.message import WsMessage
from .lib.payload import Payloads
import uuid
import traceback

logger = logging.getLogger(__name__)
logging.basicConfig()


class Client:
    def __init__(self, local_name, loop = None, port=13254):
        logger.setLevel(logging.DEBUG)
        self.uri = f"ws://localhost:{port}"        
        self.local_name = local_name
        self.websocket = None
        self.routes = {}
        self.listeners = {}
        
        self.loop = loop or asyncio.get_running_loop()
        self.authorized = False

    async def send_message(self, data):
        await self.websocket.send(json.dumps(data))
        
    async def start(self):
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(self.uri, close_timeout=0, ping_interval=None)
            logger.info("Connected to Websocket")
            await self.send_message({"type": Payloads.verification, "id":self.local_name})
            logger.info("Verification request sent")
            self.loop.create_task(self.__on_message())
            logger.info("Listening to messages")
        else:
            raise ConnectionError("Websocket is already connected!")

    def route(self, name=None):
        def route_decorator(func):
            if (name is None and func.__name__ in self.routes) or (name is not None and name in self.routes):
                raise ValueError("Route name already exists!")
            
            if not asyncio.iscoroutinefunction(func):
                raise RuntimeError("Route function must be a coro.")
            
            self.routes[name or func.__name__] = func
            return func
            
        return route_decorator
    
    def get_response(
        self,
        _uuid: str,
        loop: asyncio.AbstractEventLoop,
        check = None,
        timeout: int = 60
    ):
        future = loop.create_future()
        self.listeners[_uuid] = (check, future)
        return asyncio.wait_for(future, timeout, loop=loop)

    async def request(
        self,
        route: str,
        source: str,
        timeout: int = 60,
        **kwargs
    ):
        '''
        Requests the server for a response.
        Resolves when the response is received matching the UUID.

        Raises:
            `RuntimeError`: If the UUID is not found.
            `asyncio.TimeoutError`: If the response is not received within the timeout.
        '''
        if self.websocket is not None and self.websocket.open:
            logger.info("Requesting IPC Server for %r with data %r", route, kwargs)
        
            _uuid = str(uuid.uuid4())
            payload = {
                "uuid": _uuid,
                "type": Payloads.request,
                "id":self.local_name,
                "destination": source,
                "route": route,
                "data": kwargs
            }
            logger.debug("Client > %r", payload)

            await self.send_message(payload)
            recv = await self.get_response(_uuid, self.loop, timeout=timeout)
            logger.debug("Client < %r", recv)
            return recv

    async def __on_message(self):
        while True:
            message = WsMessage(json.loads(await self.websocket.recv()))
            if message.type.success and message.data["details"] == "Authorized":
                logger.info("Authorized Successfully")
                self.authorized = True

            elif message.type.request:
                if message.route not in self.routes:
                    logger.info("Failed to fulfill request, route not found")
                    self.loop.create_task(self.send_message({
                        "type": Payloads.error,
                        "error": "Route does not exist!",
                        "traceback": "Route does not exist!",
                        "id": self.local_name,
                        "destination": message.id,
                        "uuid": message.uuid})
                    )
                    return
                logger.info("Fulfilling request @ route: %s", message.route)
                self.loop.create_task(self._fulfill_request(message))
            
            elif message.type.response:
                logger.info(f"Received a response from server @ uuid: {message.uuid}")
                self.loop.create_task(self._dispatch(message))

            elif message.type.error:
                logger.warning(f"Failed to fulfill request: {message.error}")
    
    async def _fulfill_request(self, message: WsMessage):
        route = message.route
        func = self.routes[route]
        data = message.data
        payload = {
            "uuid": message.uuid,
            "type": Payloads.response,
            "id": self.local_name,
            "destination": message.destination,
            "data": None,
            "error": None,
            "traceback": None
        }
        try:
            result = await func(**data)
            if not isinstance(result, dict):
                result = { 'result': result }
            payload["data"] = result
        except Exception as error:
            logger.exception(error)
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = ''.join(lines)

            payload["type"] = Payloads.error
            payload["error"] = str(error)
            payload["traceback"] = traceback_text
        finally:
            self.loop.create_task(self.send_message(payload))
    
    async def _dispatch(self, msg: WsMessage):
        data = msg.data
        logger.debug('Dispatch -> %r', data)
        _uuid = msg.uuid
        if _uuid is None:
            raise RuntimeError('UUID is missing.')
        
        logger.debug('Listeners: %r', self.listeners)
        for key, val in self.listeners.items():
            if key == _uuid:
                check = val[0]
                future: asyncio.Future = val[1]

                def _check(*args):
                    return True

                if check is None:
                    check = _check
                
                if check(data):
                    future.set_result(data)
                else:
                    future.set_exception(
                        RuntimeError(f'Check failed for UUID {_uuid}')
                    )
