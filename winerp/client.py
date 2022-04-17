import asyncio
from types import FunctionType
import websockets
import json
import logging
from .lib.message import WsMessage
from .lib.payload import Payloads, MessagePayload
from .lib.errors import *
import uuid
import traceback
from typing import (
    Any,
    Callable,
    Coroutine,
    TypeVar,
    Union,
    Dict,
    Tuple,
)

logger = logging.getLogger(__name__)
Coro = TypeVar('Coro', bound=Callable[..., Coroutine[Any, Any, Any]])

class Client:
    r"""Represents a winerp Client.
    This class is used to interact with the Server

    Parameters
    -----------
    local_name: :class:`str`
        The name which will be used to refer to this client.
        This should be unique to all the clients.
    port: Optional[:class:`int`]
        The port on which the server is running. Defaults to 13254.
    """
    def __init__(
        self,
        local_name: str,
        port: int = 13254
    ):
        self.uri = f"ws://localhost:{port}"        
        self.local_name = local_name
        self.websocket = None
        self.__routes = {}
        self.listeners = {}
        self.event_listeners: Dict[str, Tuple[asyncio.Future, Callable]] = {}
        self._authorized = False
        self._on_hold = False
        self.events = [
            "on_winerp_connect",
            "on_winerp_ready",
            "on_winerp_disconnect",
            "on_winerp_request",
            "on_winerp_response",
            "on_winerp_information",
            "on_winerp_error"
        ]
    
    async def __empty_event(self, *args, **kwargs):
        ...

    def get_event(self, key):
        return self.events.get(key) or self.__empty_event
    
    @property
    def authorized(self) -> bool:
        '''
        :class:`bool`: Returns if the client is authorized by the server.
        '''
        return self._authorized
    
    @property
    def on_hold(self) -> bool:
        '''
        :class:`bool`: Returns True if the client is on hold by the server. A client is put on hold if a client of same local name is already connected to the server.
        '''
        return self._on_hold

    async def send_message(self, data: Union[Any, WsMessage]):
        if not isinstance(data, WsMessage):
            data = data.__dict__

        await self.websocket.send(json.dumps(data))
    
    def __send_message(self, data):
        asyncio.create_task(self.send_message(data))
    
    async def start(self) -> None:
        '''|coro|

        Connects the client to the server.

        Raises
        -------
            ConnectionError
                If the websocket is already connected.
        
        Returns
        -------
            :class:`None`
        '''
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(self.uri, close_timeout=0, ping_interval=None)
            self._dispatch_event('winerp_connect')
            logger.info("Connected to Websocket")
            payload = MessagePayload(
                type = Payloads.verification,
                id = self.local_name,
                uuid = str(uuid.uuid4())
            )
            await self.send_message(payload)
            logger.info("Verification request sent")
            asyncio.create_task(self.__on_message())
            logger.info("Listening to messages")
        else:
            raise ConnectionError("Websocket is already connected!")

    def route(self, name: str = None):
        '''
        A decorator to register your route. The route name should be unique.

        Raises
        -------
            ValueError
                Route name already exists.
            InvalidRouteType
                The function passed is not a coro.
        '''
        def route_decorator(func):
            if (name is None and func.__name__ in self.__routes) or (name is not None and name in self.__routes):
                raise ValueError("Route name is already registered!")
            
            if not asyncio.iscoroutinefunction(func):
                raise InvalidRouteType("Route function must be a coro.")
            
            self.__routes[name or func.__name__] = func
            return func
            
        if isinstance(name, FunctionType):
            func = name
            name = name.__name__
            return route_decorator(func)
        else:
            return route_decorator
    
    async def ping(self, client = None, timeout: int = 60) -> bool:
        '''|coro|

        Pings the client and returns back if the ping was successful.

        Raises
        -------
            ClientNotReadyError
                The client is currently not ready to send or accept requests.
            UnauthorizedError
                The client isn't authorized by the server.
        
        Returns
        --------
            :class:`bool`
                If the ping is successful, it returns True.
        '''
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")
        logger.debug("Pinging IPC Server")
        
        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type = Payloads.ping,
            id = self.local_name,
            destination = client,
            uuid = _uuid
        )
        await self.send_message(payload)
        resp = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=timeout)
        return resp.get("success", False)

    def __get_response(
        self,
        _uuid: str,
        loop: asyncio.AbstractEventLoop,
        timeout: int = 60
    ):
        future = loop.create_future()
        self.listeners[_uuid] = (None, future)
        return asyncio.wait_for(future, timeout, loop=loop)

    async def request(
        self,
        route: str,
        source: str,
        timeout: int = 60,
        **kwargs
    ) -> any:
        '''|coro|

        Requests the server for a response.
        Resolves when the response is received matching the UUID.

        Parameters
        -----------
        route: :class:`str`
            The route to request to.
        source: :class:`str`
            The destination
        timeout: :class:`int`
            Time to wait before raising :class:`~asyncio.TimeoutError`.

        Raises
        -------
            ClientNotReadyError
                The client is currently not ready to send or accept requests.
            UnauthorizedError
                The client isn't authorized by the server.
            ValueError:
                Missing either route or source or both.
            RuntimeError
                If the UUID is not found.
            asyncio.TimeoutError
                If the response is not received within the timeout.
        
        Returns
        --------
            :class:`any`
                The data associated with the message.
        '''
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")
            
            if not route or not source:
                raise ValueError("Missing required information for this request")

            logger.info("Requesting IPC Server for %r", route)
        
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
            recv = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=timeout)
            return recv
        
        else:
            raise ClientNotReadyError("The client has not been started or has disconnected")

    async def inform(
        self,
        data: any,
        destinations: list
    ):
        '''|coro|

        Sends data to other connected clients. There is no tracking of the data so there won't be any error
        if it doesn't reach its specified destination.

        The data is sent to all connected clients if the destinations list is empty.

        Parameters
        -----------
        data: :class:`Any`
            The data to redirect.
        destination: :class:`list`
            The list of destinations.

        Raises
        -------
            ClientNotReadyError
                The client is currently not ready to send or accept requests.
            UnauthorizedError
                The client isn't authorized by the server.
        
        Returns
        --------
            :class:`None`
        '''
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")

            logger.info("Informing IPC Server to redirect to routes %s" % destinations)
            if not isinstance(destinations, list):
                destinations = [destinations]

            payload = MessagePayload(
                type = Payloads.information,
                id = self.local_name,
                route = destinations,
                data = data,
            )

            await self.send_message(payload)
        else:
            raise ClientNotReadyError("The client has not been started or has disconnected")
    

    async def wait_until_ready(self):
        '''|coro|

        Waits until the client is ready to send or accept requests.        
        '''
        await self.wait_for('winerp_ready', None)

    async def wait_until_disconnected(self):
        '''|coro|
        
        Waits until the client is disconnected.
        '''
        await self.wait_for('winerp_disconnect', None)

    def wait_for(
        self,
        event: str,
        timeout: int = 60,
        check: Callable = None,
    ):
        '''|coro|

        Waits for a WebSocket event to be dispatched.

        The timeout parameter is passed onto asyncio.wait_for().
        By default, it does not timeout.

        In case the event returns multiple arguments, a tuple containing those arguments is returned instead.
        Please check the documentation for a list of events and their parameters.

        This function returns the **first event that meets the requirements.**

        Parameters
        -----------
        event: :class:`str`
            The event to wait for.
        timeout: Optional[:class:`int`]
            Time to wait before raising :class:`~asyncio.TimeoutError`. Defaults to 60.
        check: Optional[:class:`Callable`]
            A function to check if the event meets the requirements.
            If it returns True, the event is returned.
        
        Raises
        -------
            asyncio.TimeoutError
                If the event is not received within the timeout.
        
        Returns
        --------
            :class:`Any`
                The payload for the event that meets the requirements.
        '''
        future = asyncio.get_event_loop().create_future()
        if check is None:

            def _check(*args):
                return True

            check = _check

        ev = event.lower()
        try:
            listeners = self.event_listeners[ev]
        except KeyError:
            listeners = []
            self.event_listeners[ev] = listeners

        listeners.append((future, check))
        return asyncio.wait_for(future, timeout)


    async def __on_message(self):
        while True:
            try:
                message = WsMessage(json.loads(await self.websocket.recv()))
            except websockets.exceptions.ConnectionClosedError:
                self._dispatch_event('winerp_disconnect')
                break

            if message.type.success and not self._authorized:
                logger.info("Authorized Successfully")
                self._dispatch_event('winerp_ready')
                self._authorized = True
                self._on_hold = False

            elif message.type.ping:
                logger.debug("Received a ping from server")
                asyncio.create_task(self._dispatch(message))

            elif message.type.request:
                if message.route not in self.__routes:
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
                asyncio.create_task(self._fulfill_request(message))
                self._dispatch_event('winerp_request')
            
            elif message.type.response:
                logger.info("Received a response from server @ uuid: %s" % message.uuid)
                asyncio.create_task(self._dispatch(message))
                self._dispatch_event('winerp_response')

            elif message.type.error:
                if message.data == "Already authorized.":
                    self._on_hold = True
                    logger.warn("Another client is already connected. Requests will be enabled when the other is disconnected.")
                else:
                    logger.debug("Failed to fulfill request: %s" % message.data)
                    self._dispatch_event('winerp_error', message.data)

                if message.uuid is not None:
                    asyncio.create_task(self._dispatch(message))

            elif message.type.information:
                if message.data:
                    logger.info("Received an information bit from client: %s" % message.id)
                    self._dispatch_event('winerp_information', message.data, message.id)
                

    
    async def _fulfill_request(self, message: WsMessage):
        route = message.route
        func = self.__routes[route]
        data = message.data
        payload = MessagePayload().from_message(message)
        payload.type = Payloads.response
        payload.id = self.local_name
        payload.data = {}

        try:
            payload.data = await func(**data)
            json.dumps(payload.data) #Ensuring data is serializable
        except Exception as error:
            logger.exception(error)
            self._dispatch_event('winerp_error', error)
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

    def event(self, func: Coro, /) -> Coro:
        '''
        Registers a function for the event.

        The available events are:
            | ``on_winerp_connect``: The client has successfully connected to the server.
            | ``on_winerp_ready``: The client is ready to recieve and send requests.
            | ``on_winerp_disconnect``: The client has disconnected from the server.
            | ``on_winerp_request``: The server sent new request.
            | ``on_winerp_response``: The server sent back a response to a previous request.
            | ``on_winerp_information``: The server sent some data sourced by a client.
            | ``on_winerp_error``: An error occured during request processing.
        
        Raises
        -------
            NameError
                Invalid winerp event name.
            TypeError
                The event function is not a coro.
        '''
        if func.__name__ not in self.events:
            raise NameError("Invalid winerp event")
        
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Event function must be a coro.")

        setattr(self, func.__name__, func)
        logger.debug(('%s has successfully been registered as an event', func.__name__))
        return func

    def _dispatch_event(self, event_name: str, *args, **kwargs):
        logger.debug('Event Dispatch -> %r', event_name)
        
        for ev, data in self.event_listeners.items():
            if ev == event_name:
                for fut, check in data:            
                    if check(*args, **kwargs):
                        fut.set_result(None)
                        logger.debug('Event %r has been dispatched', event_name)

        try:
            coro = getattr(self, f'on_{event_name}')
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, f'on_{event_name}', *args, **kwargs)

    
    def _schedule_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> asyncio.Task:
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return asyncio.create_task(wrapped, name=f'winerp: {event_name}')
    

    async def _run_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        try:
            await coro(*args, **kwargs)
        except Exception:
            # TODO
            traceback.print_exc()
