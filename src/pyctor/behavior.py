from contextlib import _AsyncGeneratorContextManager
from logging import getLogger
from typing import Awaitable, Callable, Generic, Type

import trio

import pyctor._util
import pyctor.ref
import pyctor.signals
import pyctor.types

logger = getLogger(__name__)


class BehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T], pyctor.types.Behavior[pyctor.types.T]):
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
        # if the type is given, we assert on it here
        if self._type:
            assert issubclass(type(msg), self._type), "Can only handle messages derived from type " + str(self._type) + ", got " + str(type(msg))
        return await self._behavior(msg)


class SuperviseBehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T], pyctor.types.Behavior[pyctor.types.T]):
    """
    Will wrap a BehaviorHandler in a supervise strategy
    """

    _strategy: Callable[[Exception], Awaitable[pyctor.signals.BehaviorSignal]]
    _behavior: pyctor.types.BehaviorHandler[pyctor.types.T]

    def __init__(
        self,
        strategy: Callable[[Exception], Awaitable[pyctor.signals.BehaviorSignal]],
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
    _behavior: Callable[[], _AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]]]

    def __init__(
        self,
        behavior: Callable[[], _AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]]],
        channel: trio.abc.ReceiveChannel[pyctor.types.T],
    ) -> None:
        super().__init__()
        self._channel = channel
        self._behavior = behavior

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
                try:
                    while True:
                        msg = await self._channel.receive()
                        new_behavior = await b.handle(msg)
                        match new_behavior:
                            case Behaviors.Ignore:
                                print(f"Message ignored: {msg}")
                            case Behaviors.Same:
                                pass
                            case Behaviors.Stop:
                                await self._channel.aclose()
                                run = False
                            case Behaviors.Restart:
                                # restart the behavior
                                break
                            case pyctor.types.BehaviorHandler():
                                # TODO: Needs to be tested if that works
                                behavior = pyctor._util.to_contextmanager(new_behavior)
                                break
                except trio.EndOfChannel:
                    # actor will be stopped
                    # catch exception to enable teardown of behavior
                    run = False


class Behaviors:
    Same: pyctor.signals.BehaviorSignal = pyctor.signals.BehaviorSignal(1)
    """
    Indicates that the Behavior should stay the same for the next message.
    """

    Stop: pyctor.signals.BehaviorSignal = pyctor.signals.BehaviorSignal(2)
    """
    Indicates that the Behavior wants to be stopped. 
    A Behavior will get a final 'Stopped' LifecycleSignal and will then be terminated.
    """

    Restart: pyctor.signals.BehaviorSignal = pyctor.signals.BehaviorSignal(3)
    """
    Indicates that a Behavior wants to be restarted. 
    That means that the Behavior receives a 'Stopped' and then 'Started' LifecycleSignal.
    Also means that the setup (if available) of the Behavior will be executed again.
    """

    Ignore: pyctor.signals.BehaviorSignal = pyctor.signals.BehaviorSignal(4)
    """
    Indicates that the message was not handled and ignored. Will emit a warning
    """

    @staticmethod
    def receive(
        func: Callable[[pyctor.types.T], Awaitable[pyctor.types.Behavior[pyctor.types.T]]],
        type_check: Type[pyctor.types.T] | None = None,
    ) -> pyctor.types.Behavior[pyctor.types.T]:
        """
        Defines a Behavior that handles custom messages as well as lifecycle signals.
        """
        return BehaviorHandlerImpl(behavior=func, type_check=type_check)

    @staticmethod
    def supervise(
        strategy: Callable[[Exception], Awaitable[pyctor.signals.BehaviorSignal]],
        behavior: pyctor.types.Behavior[pyctor.types.T],
    ) -> pyctor.types.Behavior[pyctor.types.T]:
        # narrow class down to a BehaviorImpl
        assert isinstance(behavior, pyctor.types.BehaviorHandler), "The supervised behavior needs to implement the BehaviorHandler"
        return SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=behavior)
