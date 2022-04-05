class Payloads:
    '''
    Specifies all the payloads available in the system.
    This is a low level class for :meth:`~PayloadTypes`.
    '''
    success = 0
    verification = 1
    request = 2
    response = 3
    error = 4

class PayloadTypes:

    def __init__(self, type: int) -> None:
        '''
        Specifies the type of message.
        Available Types:

        `success`: Successful authorization.
        `verification`: Verification request.
        `request`: Request for a route.
        `response`: Response to a request.
        `error`: Error response.
        '''
        self._type = type
    
    @property
    def success(self) -> bool:
        '''
        Returns `True` if the message is a success message.
        '''
        return self._type == Payloads.success

    @property
    def verification(self) -> bool:
        '''
        Returns `True` if the message is a verification message.
        '''
        return self._type == Payloads.verification
    
    @property
    def request(self) -> bool:
        '''
        Returns `True` if the message is a request message.
        '''
        return self._type == Payloads.request
    
    @property
    def response(self) -> bool:
        '''
        Returns `True` if the message is a response message.
        '''
        return self._type == Payloads.response
    
    @property
    def error(self) -> bool:
        '''
        Returns `True` if the message is an error message.
        '''
        return self._type == Payloads.error

