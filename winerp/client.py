"""
Winerp- An IPC based on Websockets. Fast, Stable, and easy-to-use,
for inter-communication between your processes or discord.py bots. 
"""
# pylint: disable=E0401,W0718,C0301
import asyncio
import logging
import traceback
import typing
import uuid
from types import FunctionType
from typing import (
    Any,
    Callable,
    Coroutine,
    TypeVar,
    Union,
)

import orjson
import websockets

from .lib.errors import (
    ClientNotReadyError,
    ClientRuntimeError,
    InvalidRouteType,
    UnauthorizedError,
    MissingUUIDError,
    UUIDNotFoundError,
)
from .lib.events import Events
from .lib.message import WsMessage
from .lib.payload import Payloads, MessagePayload, winerpObject, responseObject

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
    host: Optional[:class:`str`]
        The port on which the server is running. Defaults to localhost.
    port: Optional[:class:`int`]
        The port on which the server is running. Defaults to 13254.
    reconnect: Optional[:class:`bool`]
        If set to True, the client will automatically try to reconnect to the winerp server
        every 60 seconds (default). This option is set to True by default.
    """

    def __init__(
            self,
            local_name: str,
            host: str = "localhost",
            port: int = 13254,
            reconnect: bool = True
    ):
        self.uri: str = f"ws://{host}:{port}"
        self.local_name: str = local_name
        self.reconnect: bool = reconnect
        self.reconnect_threshold: int = 60
        self.max_data_size: float = 2  # MiB
        self.websocket = None
        self.__routes = {}
        self.__sub_routes = {}
        self.listeners = {}

        self._authorized: bool = False
        self._on_hold = False
        self.__events = Events(logger)
        self.event = self.__events.event

    @property
    def authorized(self) -> bool:
        """
        :class:`bool`: Returns if the client is authorized by the server.
        """
        return self._authorized

    @property
    def on_hold(self) -> bool:
        """
        :class:`bool`: Returns True if the client is on hold by the server.
        A client is put on hold if a client of same local name is already connected to the server.
        """
        return self._on_hold

    async def send_message(self, data: Union[Any, WsMessage]):
        """Send a message to the server."""
        if not isinstance(data, WsMessage):
            data = data.__dict__
        logger.debug(data)
        await self.websocket.send(orjson.dumps(data).decode("utf-8"))

    def __send_message(self, data):
        asyncio.create_task(self.send_message(data))

    async def __verify_client(self):
        payload = MessagePayload(
            type=Payloads.verification,
            id=self.local_name,
            uuid=str(uuid.uuid4())
        )
        await self.send_message(payload)
        logger.info("Verification request sent")

    async def __connect(self) -> None:
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(
                self.uri,
                close_timeout=0,
                ping_interval=None,
                max_size=int(self.max_data_size * 1048576)
            )
            self._authorized = False
            self.__events.dispatch_event('winerp_connect')
            logger.info("Connected to Websocket")

    async def __reconnect_client(self) -> bool:
        while True:
            try:
                await self.__connect()
                await self.__verify_client()
                return True
            except Exception as error:
                logger.debug("Failed to reconnect. Retrying in %ss.", self.reconnect_threshold)
                logger.error("While trying to reconnect there has been an error. %s", str(error))
                await asyncio.sleep(self.reconnect_threshold)

    async def start(self) -> None:
        """|coro|

        Connects the client to the server.

        Raises
        -------
            ConnectionError
                If the websocket is already connected.
        
        Returns
        -------
            :class:`None`
        """
        if self.websocket is None or self.websocket.closed:
            await self.__connect()
            await self.__verify_client()
            asyncio.create_task(self.__on_message())
        else:
            raise ConnectionError("Websocket is already connected!")

    def route(self, name: str = None):
        """
        A decorator to register your route. The route name should be unique.

        Raises
        -------
            ValueError
                Route name already exists.
            InvalidRouteType
                The function passed is not a coro.
        """

        def route_decorator(_route_func):
            if (name is None and _route_func.__name__ in self.__routes) or (name is not None and name in self.__routes):
                raise ValueError("Route name is already registered!")

            if not asyncio.iscoroutinefunction(_route_func):
                raise InvalidRouteType("Route function must be a coro.")

            self.__routes[name or _route_func.__name__] = _route_func
            return _route_func

        if isinstance(name, FunctionType):
            _route_func = name
            name = name.__name__
            return route_decorator(_route_func)
        else:
            return route_decorator

    async def add_route(self, callback: typing.Callable, name: str = None):
        """|coro|
        A function to register a route. Either a decorator or this function can be used
        to register a route.

        Parameters
        ----------
        callback
        name

        Returns
        -------
        typing.Callable

        Raises
        -------
            KeyError
                Route name already exists.
            InvalidRouteType
                The function passed is not a coro.

        """
        if (name in self.__routes) or (callback.__name__ in self.__routes):
            raise KeyError(f"Route name is already registered!\nRoutes: {self.__routes}")
        if not asyncio.iscoroutinefunction(callback):
            raise InvalidRouteType('Route callback must be an asyncio coro.')

        self.__routes[name or callback.__name__] = callback
        return callback

    def remove_route(self, name: str):
        """
        Removes a route from the registered routes.
        
        Parameters
        ----------
        name
            The name of the route to be removed.

        Returns
        -------
        None

        Raises
        -------
            KeyError
                Route name does not exist.
        """
        if name in self.__routes:
            del self.__routes[name]
        else:
            raise KeyError(f"Route name {name} does not exist!")

    async def __purge_sub_routes(self, timeout, _uuid):
        await asyncio.sleep(timeout)
        del self.__sub_routes[_uuid]

    def __register_object_funcs(self, winerp_object: winerpObject):
        self.__sub_routes[winerp_object.uuid] = {}
        for function_name, function_object in winerp_object.functions.items():
            self.__sub_routes[winerp_object.uuid][function_name] = function_object
        asyncio.create_task(self.__purge_sub_routes(
            winerp_object.object_expiry, winerp_object.uuid
        ))

    async def ping(self, client=None, timeout: int = 60) -> bool:
        """|coro|

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
        """
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")
        logger.debug("Pinging IPC Server")

        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type=Payloads.ping,
            id=self.local_name,
            destination=client,
            uuid=_uuid
        )
        await self.send_message(payload)
        resp = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=timeout)
        return resp.get("success", False)

    async def _call_function(self, destination, object_identifier, func_name, *args, **kwargs) -> bool:
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")
        logger.debug("Calling a function IPC Server")

        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type=Payloads.function_call,
            id=self.local_name,
            destination=destination,
            uuid=_uuid,
            data={
                "__uuid__": object_identifier,
                "__func__": func_name,
                "__args__": list(args),
                "__kwargs__": dict(kwargs)
            }
        )
        await self.send_message(payload)
        recv = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=30)
        return recv

    def __get_response(
            self,
            _uuid: str,
            loop: asyncio.AbstractEventLoop,
            timeout: int = 60
    ):
        future = loop.create_future()
        self.listeners[_uuid] = future
        return asyncio.wait_for(future, timeout)

    async def request(
            self,
            route: str,
            source: str,
            timeout: int = 60,
            **kwargs
    ) -> Any:
        """|coro|

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
            :class:`Any`
                The data associated with the message.
        """
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
                type=Payloads.request,
                id=self.local_name,
                destination=source,
                route=route,
                data=kwargs,
                uuid=_uuid
            )

            await self.send_message(payload)
            recv = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=timeout)
            return recv

        else:
            raise ClientNotReadyError("The client has not been started or has disconnected")

    async def get_clients(self, timeout: int = 60) -> list:
        """|coro|

        Gets all the connected clients.

        Raises
        -------
            ClientNotReadyError
                The client is currently not ready to send or accept requests.
            UnauthorizedError
                The client isn't authorized by the server.
        
        Returns
        --------
            :class:`list`
                A list of connected clients.
        """
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")

        logger.debug("Getting all connected clients")
        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type=Payloads.client_count,
            id=self.local_name,
            uuid=_uuid
        )
        await self.send_message(payload)
        resp = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=timeout)
        return resp


    async def inform(
            self,
            data: Any,
            destinations: list
    ):
        """|coro|

        Sends data to other connected clients. There is no tracking of the data so there 
        won't be any error if it doesn't reach its specified destination.

        The data is sent to all connected clients if the destinations list is empty.

        Parameters
        -----------
        data: :class:`Any`
            The data to redirect.
        destinations: :class:`list`
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
        """
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError("The client is currently not ready to send or accept requests.")
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")

            logger.info("Informing IPC Server to redirect to routes %s", destinations)
            if not isinstance(destinations, list):
                destinations = [destinations]

            payload = MessagePayload(
                type=Payloads.information,
                id=self.local_name,
                route=destinations,
                data=data,
            )

            await self.send_message(payload)
        else:
            raise ClientNotReadyError("The client has not been started or has disconnected")

    async def wait_until_ready(self):
        """|coro|

        Waits until the client is ready to send or accept requests.        
        """
        await self.wait_for('winerp_ready', None)

    async def wait_until_disconnected(self):
        """|coro|
        
        Waits until the client is disconnected.
        """
        await self.wait_for('winerp_disconnect', None)

    def wait_for(
            self,
            event: str,
            timeout: Union[int, None] = None,
    ):
        """|coro|

        Waits for a WebSocket event to be dispatched.

        The timeout parameter is passed onto asyncio.wait_for().
        By default, it does not have timeout.

        In case the event returns multiple arguments, a tuple containing those arguments is returned instead.
        Please check the documentation for a list of events and their parameters.

        This function returns the **first event that meets the requirements.**

        Parameters
        -----------
        event: :class:`str`
            The event to wait for.
        timeout: Optional[:class:`int`]
            Time to wait before raising :class:`~asyncio.TimeoutError`. Defaults to 60.

        Raises
        -------
            asyncio.TimeoutError
                If the event is not received within the timeout.
        
        Returns
        --------
            :class:`Any`
                The payload for the event that meets the requirements.
        """
        future = asyncio.get_event_loop().create_future()

        _event = event.lower()
        try:
            listeners = self.__events.listeners[_event]
        except KeyError:
            listeners = []
            self.__events.listeners[_event] = listeners

        listeners.append(future)
        return asyncio.wait_for(future, timeout)

    async def __on_message(self):
        logger.info("Listening to messages")
        message = None
        while True:
            try:
                message = WsMessage(orjson.loads(await self.websocket.recv()))
            except websockets.exceptions.ConnectionClosedError:
                self.__events.dispatch_event('winerp_disconnect')
                if self.reconnect:
                    if not await self.__reconnect_client():
                        break
                else:
                    break

            if message.type.success and not self._authorized:
                logger.info("Authorized Successfully")
                self.__events.dispatch_event('winerp_ready')
                self._authorized = True
                self._on_hold = False

            elif message.type.ping:
                logger.debug("Received a ping from server")
                asyncio.create_task(self._dispatch(message))

            elif message.type.request:
                if message.route not in self.__routes:
                    logger.info("Failed to fulfill request, route not found")
                    payload = MessagePayload(
                        type=Payloads.error,
                        id=self.local_name,
                        data="Route not found",
                        traceback="Route not found",
                        destination=message.id,
                        uuid=message.uuid
                    )
                    self.__send_message(payload)
                    return
                logger.info("Fulfilling request @ route: %s", message.route)
                asyncio.create_task(self._fulfill_request(message))
                self.__events.dispatch_event('winerp_request')

            elif message.type.response:
                logger.info("Received a response from server @ uuid: %s", message.uuid)
                asyncio.create_task(self._dispatch(message))
                self.__events.dispatch_event('winerp_response')

            elif message.type.error:
                if message.data == "Already authorized.":
                    self._on_hold = True
                    logger.warning(
                        "Another client is already connected. Requests will be enabled when the other is disconnected.")
                else:
                    logger.debug("Failed to fulfill request: %s", message.data)
                    self.__events.dispatch_event('winerp_error', message.data)

                if message.uuid is not None:
                    asyncio.create_task(self._dispatch(message))

            elif message.type.information:
                if message.data:
                    logger.debug("Received an information bit from client: %s", message.id)
                    self.__events.dispatch_event('winerp_information', message.data, message.id)

            elif message.type.client_count:
                logger.debug("Received the response of the client_count from server")
                asyncio.create_task(self._dispatch(message))

            elif message.type.function_call:
                logger.debug("Received an object function call.")
                logger.debug(message.data)
                payload = MessagePayload(
                    type=Payloads.response,
                    id=self.local_name,
                    destination=message.id,
                    uuid=message.uuid
                )
                try:
                    called_function = self.__sub_routes[message.data["__uuid__"]][message.data["__func__"]]
                    asyncio.create_task(
                        self._fulfil_callback(
                            payload,
                            called_function,
                            *message.data["__args__"],
                            **message.data["__kwargs__"]
                        )
                    )
                except KeyError:
                    payload = MessagePayload(
                        type=Payloads.error,
                        id=self.local_name,
                        data="The called function has either expired or has never been registered",
                        traceback="The called function has either expired or has never been registered",
                        destination=message.id,
                        uuid=message.uuid
                    )
                    self.__send_message(payload)

    def __parse_object(self, payload):
        payload.pseudo_object = True
        dummy_object = payload.data
        payload.data = dummy_object.serialize()
        self.__register_object_funcs(dummy_object)

    async def _fulfil_callback(self, payload, function, *args, **kwargs):
        try:
            payload.data = await function(*args, **kwargs)
            if not isinstance(payload.data, (int, float, str, bool, type(None), list, tuple, dict)):
                payload.data = winerpObject(payload.data)

            if isinstance(payload.data, winerpObject):
                self.__parse_object(payload)

            self.__send_message(payload)
        except Exception as error:
            logger.exception("Failed to run the registered method")
            self.__events.dispatch_event('winerp_error', error)
            payload.type = Payloads.error
            payload.data = str(error)
            payload.traceback = ''.join(
                traceback.format_exception(
                    TypeError, error, error.__traceback__
                )
            )

    async def _fulfill_request(self, message: WsMessage):
        route = message.route
        func = self.__routes[route]
        data = message.data
        payload = MessagePayload().from_message(message)
        payload.type = Payloads.response
        payload.id = self.local_name

        try:
            payload.data = await func(message.destination, **data)
            if isinstance(payload.data, winerpObject):
                self.__parse_object(payload)
        except Exception as error:
            logger.exception(error)
            self.__events.dispatch_event('winerp_error', error)
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = ''.join(lines)

            payload.type = Payloads.error
            payload.data = str(error)
            payload.traceback = traceback_text
        finally:
            try:
                await self.send_message(payload)
            except TypeError as error:
                logger.exception("Failed to convert data to json")
                self.__events.dispatch_event('winerp_error', error)
                payload.type = Payloads.error
                payload.data = str(error)
                payload.traceback = ''.join(
                    traceback.format_exception(
                        TypeError,
                        error,
                        error.__traceback__
                    )
                )
                self.__send_message(payload)

    async def _dispatch(self, msg: WsMessage):
        data = msg.data
        _uuid = msg.uuid
        if _uuid is None:
            raise MissingUUIDError('UUID is missing.')
        if _uuid not in self.listeners:
            raise UUIDNotFoundError(f"UUID {_uuid} not found in listeners.")

        future: asyncio.Future = self.listeners[_uuid]
        if not msg.type.error:
            if msg.pseudo_object:
                future.set_result(responseObject(self, msg.id, data))
            else:
                future.set_result(data)
        else:
            future.set_exception(
                ClientRuntimeError(msg.data)
            )
