from .payload import PayloadTypes

class WsMessage:

    def __init__(self, message: dict):
        self._message = message
    
    def __repr__(self) -> str:
        return f'<winerp.WsMessage uuid={self.uuid} type={self.type.__repr__()}>'
    
    @property
    def type(self) -> PayloadTypes:
        '''
        Returns the type of the message.
        '''
        return PayloadTypes(self._message["type"])
    
    @property
    def id(self) -> int:
        '''
        Returns the id of the bot.
        '''
        return self._message.get("id")
    
    @property
    def destination(self) -> str:
        '''
        Returns the destination of the message.
        '''
        return self._message.get("destination")
    
    @property
    def route(self) -> str:
        '''
        Returns the route of the message.
        '''
        return self._message.get("route")
    
    @property
    def uuid(self) -> str:
        '''
        Returns the unique id associated with this message.
        '''
        return self._message.get("uuid")
    
    @property
    def data(self) -> any:
        '''
        Returns the data associated with the message.
        '''
        return self._message.get("data")
    
    @property
    def error(self) -> str:
        '''
        Returns the error associated with the message.
        '''
        return self._message.get("error")
    
    @error.setter
    def error(self, error: str):
        '''
        Sets the error associated with the message.
        '''
        self._message["error"] = error
    
    @property
    def traceback(self) -> str:
        '''
        Returns the error associated with the message.
        '''
        return self._message.get("traceback")
    
    @traceback.setter
    def traceback(self, traceback: str):
        '''
        Sets the error associated with the message.
        '''
        self._message["traceback"] = traceback

    def to_dict(self) -> dict:
        '''
        Returns the message as a `dict` type.
        '''
        return {
            'type': self.type,
            'id': self.id,
            'destination': self.destination,
            'route': self.route,
            'uuid': self.uuid,
            'data': self.data,
            'error': self.error,
            'traceback': self.traceback
        }