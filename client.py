import asyncio
from aioredis import ConnectionClosedError
import websockets
import json
import logging
from .lib.message import WsMessage
from .lib.payload import Payloads, MessagePayload
from .lib.errors import *
import uuid
import traceback

logger = logging.getLogger(__name__)

class Client:
    def __init__(self, local_name, loop = None, port=13254):
        self.uri = f"ws://localhost:{port}"        
        self.local_name = local_name
        self.websocket = None
        self.routes = {}
        self.listeners = {}
        
        self.loop = loop or asyncio.get_running_loop()
        self.authorized = False
        self.events = {
            "on_winerp_connect": None,
            "on_winerp_ready": None,
            "on_winerp_disconnect": None,
            "on_winerp_request": None,
            "on_winerp_response": None
        }
    
    async def __empty_event(self, *args, **kwargs):
        ...

    def get_event(self, key):
        return self.events.get(key) or self.__empty_event

    @property
    def url(self):
        '''
        Returns back the url of the websocket.
        '''
        return self.uri

    async def send_message(self, data):
        if not isinstance(data, dict):
            data = data.to_dict()
        await self.websocket.send(json.dumps(data))
    
    def __send_message(self, data):
        self.loop.create_task(self.send_message(data))
        
    async def start(self):
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(self.uri, close_timeout=0, ping_interval=None)
            self.loop.create_task(self.get_event("on_winerp_connect")())
            logger.info("Connected to Websocket")
            payload = MessagePayload(
                type = Payloads.verification,
                id = self.local_name,
                uuid = str(uuid.uuid4())
            )
            await self.send_message(payload)
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
                raise InvalidRouteType("Route function must be a coro.")
            
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
            if not self.authorized:
                raise UnauthorizedError("Client is not authorized!")
            
            logger.info("Requesting IPC Server for %r with data %r", route, kwargs)
        
            _uuid = str(uuid.uuid4())
            payload = MessagePayload(
                type = Payloads.request,
                id = self.local_name,
                destination = source,
                route = route,
                data = kwargs,
                uuid = _uuid
            )

            await self.send_message(payload)
            recv = await self.get_response(_uuid, self.loop, timeout=timeout)
            return recv

    async def __on_message(self):
        while True:
            try:
                message = WsMessage(json.loads(await self.websocket.recv()))
            except websockets.exceptions.ConnectionClosedError:
                self.loop.create_task(self.get_event("on_winerp_disconnect")())
                break

            if message.type.success and not self.authorized:
                logger.info("Authorized Successfully")
                self.loop.create_task(self.get_event("on_winerp_ready")())
                self.authorized = True

            elif message.type.request:
                if message.route not in self.routes:
                    logger.info("Failed to fulfill request, route not found")
                    payload = MessagePayload(
                        type = Payloads.error,
                        id = self.local_name,
                        data = "Route not found",
                        traceback = "Route not found",
                        destination = message.id,
                        uuid = message.uuid
                    )
                    self.__send_message(payload)
                    return
                logger.info("Fulfilling request @ route: %s" % message.route)
                self.loop.create_task(self._fulfill_request(message))
                self.loop.create_task(self.get_event("on_winerp_request")())
            
            elif message.type.response:
                logger.info("Received a response from server @ uuid: %s" % message.uuid)
                self.loop.create_task(self._dispatch(message))
                self.loop.create_task(self.get_event("on_winerp_response")())

            elif message.type.error:
                logger.debug("Failed to fulfill request: %s" % message.error)
                if message.uuid is not None:
                    self.loop.create_task(self._dispatch(message))
    
    async def _fulfill_request(self, message: WsMessage):
        route = message.route
        func = self.routes[route]
        data = message.data
        payload = MessagePayload().from_message(message)
        payload.type = Payloads.response
        payload.id = self.local_name
        payload.data = {}

        try:
            payload.data = await func(**data)
        except Exception as error:
            logger.exception(error)
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = ''.join(lines)

            payload.type = Payloads.error
            payload.data = str(error)
            payload.traceback = traceback_text
        finally:
            self.__send_message(payload)
    
    async def _dispatch(self, msg: WsMessage):
        data = msg.data
        logger.debug('Dispatch -> %r', data)
        _uuid = msg.uuid
        if _uuid is None:
            raise MissingUUIDError('UUID is missing.')
        
        found = False
        for key, val in self.listeners.items():
            if key == _uuid:
                found = True
                check = val[0]
                future: asyncio.Future = val[1]

                def _check(*args):
                    return True

                if check is None:
                    check = _check
                
                if not msg.type.error:
                    if check(data):
                        future.set_result(data)
                    else:
                        future.set_exception(
                            CheckFailureError(f"Check failed for UUID {_uuid}")
                        )
                else:
                    future.set_exception(
                        ClientRuntimeError(msg.data)
                    )
        if not found:
            raise UUIDNotFoundError(f"UUID {_uuid} not found in listeners.")

    def event(self, func):
        if func.__name__ not in self.events:
            raise NameError("Invalid winerp event")
        
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Event function must be a coro.")

        self.events[func.__name__] = func
        return func

