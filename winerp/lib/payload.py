import asyncio
from uuid import uuid4


class Payloads:
    '''
    Specifies all the payloads available in the system.
    This is a low level class for :class:`~winerp.lib.payload.PayloadTypes`.
    '''
    success = 0
    verification = 1
    request = 2
    response = 3
    error = 4
    ping = 5
    information = 6
    function_call = 7

class PayloadTypes:
    '''
    Specifies the type of message. Available Types:
        | ``success``: Successful authorization.
        | ``verification``: Verification request.
        | ``request``: Request for a route.
        | ``response``: Response to a request.
        | ``error``: Error response.
        | ``ping``: Ping message.
    '''
    def __init__(self, type: int) -> None:
        self._type = type
    
    def __repr__(self) -> str:
        return '<PayloadTypes: {}>'.format(self._type)
    
    @property
    def success(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is a success message.
        '''
        return self._type == Payloads.success

    @property
    def verification(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is a verification message.
        '''
        return self._type == Payloads.verification
    
    @property
    def request(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is a request message.
        '''
        return self._type == Payloads.request
    
    @property
    def response(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is a response message.
        '''
        return self._type == Payloads.response
    
    @property
    def error(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is an error message.
        '''
        return self._type == Payloads.error

    @property
    def ping(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is a ping message.
        '''
        return self._type == Payloads.ping

    @property
    def information(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is an information message.
        '''
        return self._type == Payloads.information

    @property
    def function_call(self) -> bool:
        '''
        :class:`bool`: Returns ``True`` if the message is an information message.
        '''
        return self._type == Payloads.function_call



class MessagePayload:
    '''
    Represent IPC payload class.
    '''
    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', None)
        self.type = kwargs.pop('type', None)
        self.route = kwargs.pop('route', None)
        self.traceback = kwargs.pop('traceback', None)
        self.data = kwargs.pop('data', {})
        self.uuid = kwargs.pop('uuid', None)
        self.destination = kwargs.pop('destination', None)
        self.pseudo_object = kwargs.pop('pseudo_object', None)
    

    def from_message(self, msg):
        '''
        Makes a payload from message. This is similar to cloning a message's ``dict`` to a new ``dict`` with same values.

        Parameters
        ----------
        msg: :class:`~winerp.lib.message.WsMessage`
            The message to clone
        
        Return Type
        -----------
        :class:`~winerp.lib.payload.MessagePayload`
        '''
        self.id = msg.id
        self.type = msg.type
        self.route = msg.route
        self.data = msg.data
        self.traceback = msg.traceback
        self.uuid = msg.uuid
        self.destination = msg.destination
        self.pseudo_object = msg.pseudo_object
        return self

    def to_dict(self) -> dict:
        '''
        Returns a ``dict`` representing the message.

        Return Type
        -----------
        :class:`dict`
        '''
        return {
            'id': self.id,
            'type': self.type,
            'route': self.route,
            'data': self.data,
            'traceback': self.traceback,
            'uuid': self.uuid,
            'destination': self.destination,
            'pseudo_object': self.pseudo_object
        }


class responseObject:
    def __init__(self, ipc_client, source, data):
        self.__ipc = ipc_client
        self.__name__ = data["__name__"]
        self.__uuid__ = data["__uuid__"]
        self.__source = source
        for each_attribute, attribute_value in data["__attr__"].items():
            self.__setattr__(each_attribute, attribute_value)

        for each_function, is_it_coro in data["__func__"].items():
            async def __async_fakeFunc(*args, **kwargs):
                return await self.__function_call(each_function, is_it_coro, *args, **kwargs)

            self.__setattr__(each_function, __async_fakeFunc)

    

    async def __function_call(self, function_name, is_it_coro, *args, **kwargs):
        return await self.__ipc.call_function(self.__source, self.__uuid__, function_name, *args, **kwargs)



class winerpObject:
    def __init__(self, object, required_functions = [], object_expiry=30, process_iters = True):
        """Creates a fake object which can be transferred to another client
        Whenever a fake object is sent to another client, the required functions are registered in the memory until the object expiry timeout.

        Args:
            object (class): The object you want to send to another client
            required_functions (list, optional): The class functions you want to execute on the client side. Defaults to [].
            object_expiry (int, optional): The time after which the object expires. Defaults to 30 seconds.
            process_iters (bool, optional): If set to True (default), all iterables with elements of datatype int, float, str, bool, & NoneType will be sent to the client.
        """
        self.object = object
        self.required_functions = required_functions
        self.object_expiry = object_expiry
        self.process_iters = process_iters
        self.uuid = str(uuid4())

    def __pythonic_object(self, var) -> bool:
        return isinstance(var, (int, float, str, bool, type(None)))

    def serialize_attributes(self):
        self.__serialized = {}
        self.functions = {}
        self.__serialized_functions = {}
        for attribute in self.object.__dir__():
            if attribute[0] == "_":
                continue
            
            try:
                attribute_value = getattr(self.object, attribute)
            except:
                continue
            if self.__pythonic_object(attribute_value):
                self.__serialized[attribute] = attribute_value
            elif callable(attribute_value):
                if attribute in self.required_functions:
                    self.functions[attribute] = attribute_value
                    self.__serialized_functions[attribute] = asyncio.iscoroutinefunction(attribute_value)
            elif isinstance(attribute_value, (list, set, tuple)):
                if self.process_iters:
                    if not any(not self.__pythonic_object(__elem) for __elem in attribute_value):
                        self.__serialized[attribute] = tuple(attribute_value) if isinstance(attribute_value, tuple) else attribute_value
            elif isinstance(attribute_value, dict):
                if self.process_iters:
                    if not any(
                        not self.__pythonic_object(key) or not self.__pythonic_object(value)
                        for key, value in attribute_value.items()):
                        self.__serialized[attribute] = attribute_value

            else:
                try:
                    if self.__pythonic_object(str(attribute_value.__str__())):
                        self.__serialized[attribute] = str(attribute_value)
                except:
                    ...
                
        return self.__serialized, self.functions

    def serialize(self):
        raw_object = self.serialize_attributes()
        return {
            "__name__": self.object.__class__.__name__,
            "__attr__": raw_object[0],
            "__func__": self.__serialized_functions,
            "__uuid__": self.uuid
        }
