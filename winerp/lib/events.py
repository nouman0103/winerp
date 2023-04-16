import asyncio
import traceback
from logging import Logger
from typing import (
    Dict,
    Callable,
    Coroutine,
    Any,
)


class Events:
    """
    This class is used as an event manager internally.
    This shouldn't be inherited as it is controlled by Client internally.

    Parameters
    -----------
    logger: :class:`logging.Logger`
    """

    def __init__(self, logger):
        self.listeners: Dict[str, asyncio.Future] = {}
        self._events_ = [
            "on_winerp_connect",
            "on_winerp_ready",
            "on_winerp_disconnect",
            "on_winerp_request",
            "on_winerp_response",
            "on_winerp_information",
            "on_winerp_error"
        ]
        self._logger: Logger = logger

    def dispatch_event(self, name: str, *args, **kwargs) -> None:
        """
        Dispatches an event.

        Parameters
        __________
        name
        *args
        **kwargs

        Returns:

        """
        self._logger.debug('Event Dispatch -> %r', name)
        try:
            for future in self.listeners[name]:
                future.set_result(None)
                self._logger.debug('Event %r has been dispatched', name)
        except KeyError:
            ...

        try:
            coro = getattr(self, f'on_{name}')
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, f'on_{name}', *args, **kwargs)

    def _schedule_event(
            self,
            coro: Callable[..., Coroutine[Any, Any, Any]],
            event_name: str,
            *args: Any,
            **kwargs: Any,
    ) -> asyncio.Task:
        """

        Args:
            coro:
            event_name:
            *args:
            **kwargs:

        Returns:

        """
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return asyncio.create_task(wrapped, name=f'winerp: {event_name}')

    async def _run_event(
            self,
            coro: Callable[..., Coroutine[Any, Any, Any]],
            name: str,
            *args: Any,
            **kwargs: Any,
    ) -> None:
        try:
            await coro(*args, **kwargs)
        except Exception:
            # TODO
            traceback.print_exc()

    def event(self, func: Coroutine, /) -> Coroutine:
        """
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
        """
        if func.__name__ not in self._events_:
            raise NameError("Invalid winerp event")

        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Event function must be a coro.")

        setattr(self, func.__name__, func)
        self._logger.debug('%s has successfully been registered as an event', func.__name__)
        return func
