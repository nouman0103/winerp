import datetime
import time
import asyncio
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
)
import uuid

class AnyObject:
    '''
    Represents any arbitary object which is returned when unpacking json data.
    '''
    def __init__(self) -> None:
        pass

async def remove_routes(client_routes: list, routes: list, after: int):
    await asyncio.sleep(after)
    for route in routes:
        if route in client_routes:
            client_routes.remove(route)

class WinerpObject:
    '''
    Represents a dummy object. This is used when you want to transfer objects over IPC.
    
    Note that this does not actually send the instance of the object. Rather it clones it and sends the clone.
    You can also choose to attach functions to the object. This will create a route for the function.

    Parameters:
    -----------
    object: object
        The object to be serialized.
    recursion_level: Optional[:class:`int`]
        The recursion level of the object. We recommend maximum of ``2``. In ideal cases, ``0`` or ``1`` should be enough.
    handle_functions: Optional[:class:`bool`]
        Whether to handle functions or not. If ``True``, functions will be converted to coroutines and added to the client routes.
    functions_list: Optional[:class:`list`]
        A list of functions to be handled. If ``None``, all functions will be handled.
    handle_iterables: Optional[:class:`bool`]
        Whether to handle iterables or not. If ``True``, iterables will be serialized (this might take time for big iterables).
    iterables_list: Optional[:class:`list`]
        A list of iterables to be handled. If ``None``, all iterables will be handled.
    delete_after: Optional[:class:`int`]
        The time in seconds after which the routes attached to the object will be deleted.
    keep_until: Optional[:class:`datetime.datetime`]
        The time after which the routes attached to the object will be deleted.
    '''
    def __init__(
        self,
        object: object,
        *,
        recursion_level: int = 0,
        handle_functions: bool = True,
        functions_list: List[str] = None,
        handle_iterables: bool = True,
        iterables_list: List[str] = None,
        delete_after: int = 45,
        keep_until: datetime.datetime = None,
    ):
        self.json = {}
        self.object = object
        self.recursion_level = recursion_level
        self.handle_functions = handle_functions
        self.functions_list = functions_list
        self.handle_iterables = handle_iterables
        self.iterables_list = iterables_list
        if keep_until is not None:
            delete_after = (keep_until - datetime.datetime.now()).total_seconds()
        self.expiry_time = time.time() + delete_after
        self._functions = []
    
    async def _to_json(
        self,
        object: object,
        client_routes: Dict[str, Callable],
    ):
        if isinstance(object, (str, int, bool)):
            return object

        _json = {}
        _dir = object.__dir__()
        for i in _dir:
            if i.startswith('_'):
                continue
            try:
                attr = getattr(object, i)
            except:
                continue

            _attr = None
            if callable(attr):
                if self.handle_functions and (self.functions_list is None or i in self.functions_list):
                    _func_uuid = str(uuid.uuid4())
                    if not asyncio.iscoroutine(attr):
                        attr = asyncio.coroutine(attr)
                    self._functions.append([i, _func_uuid])
                    client_routes[_func_uuid] = attr
                continue

            elif isinstance(attr, (list, tuple)):
                if self.recursion_level > 0 and (
                    self.handle_iterables and (self.iterables_list is None or i in self.iterables_list)
                ):
                    self.recursion_level -= 1
                    _attr = []
                    for obj in attr:
                        try:
                            _hack = obj.__dict__
                            _attr.append(_hack)
                        except:
                            _attr.append(
                                await asyncio.create_task(self._to_json(obj, client_routes))
                            )

            elif attr is None:
                pass

            elif isinstance(attr, (int, float)):
                _attr = type(attr)(attr)

            else:
                _attr = str(attr)

            _json[i] = _attr
        return _json
    
    async def _from_json(
        self,
        json: dict,
        client_routes: List[Dict[str, str]],
        request: Callable,
        source: str,
        *,
        is_nested = True
    ):
        obj = AnyObject()
        if isinstance(json, (str, int, bool)):
            return json

        for i, attr in json.items():
            _attr = None
            
            if isinstance(attr, dict):
                _attr = await self._from_json(attr, client_routes, request, source)
            
            elif isinstance(attr, list):
                _attr = []
                for at in attr:
                    _attr.append(await self._from_json(at, client_routes, request, source))
            
            elif attr is None:
                pass

            elif not callable(attr):
                _attr = attr
            
            setattr(obj, i, _attr)
        
        if not is_nested:
            for route in client_routes:
                _attr_name, _uuid = route
                _attr = lambda **kwargs: self._make_request(request, _uuid, source, **kwargs)
                setattr(obj, _attr_name, _attr)
            setattr(obj, '__json__', json)
            setattr(obj, 'is_destroyed', lambda: json['__expiry__'] <= time.time())
        return obj
    
    def _make_request(self, request, _uuid, _source, **kwargs):
        return request(_uuid, _source, 60, **kwargs)

    def __dict__(self) -> dict:
        return self.to_dict()
    
    async def to_dict(
        self,
        client_routes: Dict[str, Callable],
    ) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
        '''
        Returns a tuple of dictionary representation of the object and a list of functions to be handled.
        If the object supplied was already a dictionary, it will be returned as is.

        **Note: This should generally be avoided and should be used for aggressive debugging purposes only.**

        Parameters:
        -----------
        client: :class:`Client`
            Your ipc client to attach routes to.

        Returns:
        --------
        :class:`tuple`
            A tuple of dictionary representation of the object and a list of functions to be handled.
        '''
        object = self.object
        if isinstance(object, dict):
            return object, self._functions
        self.json = await self._to_json(object, client_routes)
        self.json['__expiry__'] = self.expiry_time
        asyncio.create_task(
            remove_routes(
                client_routes,
                self._functions,
                time.time() - self.expiry_time
            )
        )
        return (self.json, self._functions)
    
    async def to_object(self, message: object, request: Callable) -> object:
        '''
        Returns an object from the dictionalry supplied.
        If the object supplied was already an object, it will be returned as is.

        **Note: This should generally be avoided and should be used for aggressive debugging purposes only.**

        Parameters:
        -----------
        message: :class:`object`
            The message from the websocket.
        request: :class:`Callable`
            The request function to be used to make requests.
        '''
        return await self._from_json(message.data, self._functions, request, message.id, is_nested=False)
