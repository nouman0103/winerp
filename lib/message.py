from .payload import PayloadTypes

class WsMessage:

    def __init__(self, message: dict):
        self._message = message
    
    @property
    def type(self) -> PayloadTypes:
        '''
        Returns the type of the message.
        '''
        return PayloadTypes(self._message["type"])
    
    @property
    def id(self) -> int:
        '''
        Retusn the id of the bot.
        '''
        return self._message["id"]
    
    @property
    def destination(self) -> str:
        '''
        Returns the destination of the message.
        '''
        return self._message["destination"]
    
    @property
    def route(self) -> str:
        '''
        Returns the route of the message.
        '''
        return self._message["route"]
    
    @property
    def uuid(self) -> str:
        '''
        Returns the unique id associated with this message.
        '''
        return self._message["uuid"]
    
    @property
    def data(self) -> dict:
        '''
        Returns the data associated with the message.
        '''
        return self._message["data"]

    def to_dict(self) -> dict:
        '''
        Returns the message as a dictionary.
        '''
        return {
            'type': self.type,
            'id': self.id,
            'destination': self.destination,
            'route': self.route,
            'uuid': self.uuid,
            'data': self.data
        }