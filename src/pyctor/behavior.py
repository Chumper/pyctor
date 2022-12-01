from contextlib import _AsyncGeneratorContextManager
from logging import getLogger
from types import FunctionType
from typing import AsyncContextManager, Awaitable, Callable, Generic, Type

import trio

import pyctor._util
import pyctor.behaviors
import pyctor.ref
import pyctor.signals
import pyctor.types

logger = getLogger(__name__)


class BehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T]):
    """
    Class that all Behaviors need to implement if they want to be handled by Pyctor.
    This class fullfills the Protocol requirements.
    """

    _behavior: pyctor.types.BehaviorFunction[pyctor.types.T]
    _type: Type[pyctor.types.T] | None = None

    def __init__(
        self,
        behavior: pyctor.types.BehaviorFunction[pyctor.types.T],
        type_check: Type[pyctor.types.T] | None = None,
    ) -> None:
        self._behavior = behavior
        self._type = type_check

    async def handle(self, msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
        if self._type:
            # if the type is given, we assert on it here
            assert issubclass(type(msg), self._type), "Can only handle messages derived from type " + str(self._type) + ", got " + str(type(msg))
        return await self._behavior(msg)


class SuperviseBehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T]):
    """
    Will wrap a BehaviorHandler in a supervise strategy
    """

    _strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]]
    _behavior: pyctor.types.BehaviorHandler[pyctor.types.T]

    def __init__(
        self,
        strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]],
        behavior: pyctor.types.BehaviorHandler[pyctor.types.T],
    ) -> None:
        self._strategy = strategy
        self._behavior = behavior

    async def handle(self, msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
        try:
            return await self._behavior.handle(msg)
        except Exception as e:
            # run strategy
            return await self._strategy(e)


class BehaviorProcessorImpl(pyctor.types.BehaviorProcessor, Generic[pyctor.types.T]):
    _channel: trio.abc.ReceiveChannel[pyctor.types.T]
    _behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]

    def __init__(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        channel: trio.abc.ReceiveChannel[pyctor.types.T],
    ) -> None:
        super().__init__()
        self._channel = channel
        self._behavior = behavior
        assert isinstance(self._behavior, FunctionType)

    async def behavior_task(self) -> None:
        """
        The main entry point for each behavior and therefore each actor.
        This method is a single task in the trio concept.
        Everything below this Behavior happens in this task.
        """
        behavior = self._behavior
        run = True
        while run:
            async with behavior() as b:
                assert isinstance(b, pyctor.types.BehaviorHandler)
                try:
                    while True:
                        msg = await self._channel.receive()
                        new_behavior = await b.handle(msg)
                        match new_behavior:
                            case pyctor.behaviors.Behaviors.Ignore:
                                print(f"Message ignored: {msg}")
                            case pyctor.behaviors.Behaviors.Same:
                                pass
                            case pyctor.behaviors.Behaviors.Stop:
                                await self._channel.aclose()
                                run = False
                            case pyctor.behaviors.Behaviors.Restart:
                                # restart the behavior
                                break
                            case FunctionType():
                                # trust is our asserts here...
                                behavior = new_behavior
                                break
                except trio.EndOfChannel:
                    # actor will be stopped
                    # catch exception to enable teardown of behavior
                    run = False
