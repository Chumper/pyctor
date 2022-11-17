from contextlib import _AsyncGeneratorContextManager
from enum import Enum
from logging import getLogger
from typing import Awaitable, Callable

import trio

from pyctor.ref import LocalRef
from pyctor.signals import BehaviorSignal
from pyctor.types import ActorNursery, Behavior, BehaviorFunction, BehaviorHandler, BehaviorProcessor, Context, Ref, T

logger = getLogger(__name__)

class BehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Class that all Behaviors need to implement if they want to be handled by Pyctor.
    This class fullfills the Protocol requirements.
    """

    _behavior: BehaviorFunction[T]

    def __init__(self, behavior: BehaviorFunction[T]) -> None:
        self._behavior = behavior

    async def handle(self, msg: T) -> Behavior[T]:
        return await self._behavior(msg)

class SuperviseStrategy(Enum):
    Restart = 1
    Stop = 2
    Ignore = 3


class LoggingBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Logs every message that goes through the behavior
    """

    _behavior: BehaviorHandler[T]

    def __init__(self, behavior: Behavior[T]) -> None:
        self._behavior = behavior  # type: ignore

    async def handle(self, msg: T) -> "Behavior[T]":
        logger.info(f"Start handling: %s", msg)
        b = await self._behavior.handle(msg=msg)
        logger.info(f"End handling: %s", msg)
        return b


class SuperviseBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Will wrap a BehaviorHandler in a supervise strategy
    """

    _strategy: Callable[[Exception], Awaitable[SuperviseStrategy]]
    _behavior: BehaviorHandler[T]

    def __init__(self, strategy: Callable[[Exception], Awaitable[SuperviseStrategy]], behavior: BehaviorHandler[T]) -> None:
        self._strategy = strategy
        self._behavior = behavior

    async def handle(self, msg: T) -> Behavior[T]:  # type: ignore
        try:
            return await self._behavior.handle(msg)
        except Exception as e:
            # run strategy
            now_what = await self._strategy(e)
            match now_what:
                case SuperviseStrategy.Restart:
                    return Behaviors.Restart
                case SuperviseStrategy.Stop:
                    return Behaviors.Stop
                case _, SuperviseStrategy.Ignore:
                    return Behaviors.Same


class BehaviorProcessorImpl(BehaviorProcessor[T]):
    _nursery: ActorNursery
    
    _send: trio.abc.SendChannel[T]
    _receive: trio.abc.ReceiveChannel[T]

    _behavior: Callable[[], _AsyncGeneratorContextManager[BehaviorHandler[T]]]
    _ctx: Context[T]

    def __init__(self, nursery: ActorNursery, behavior: Callable[[], _AsyncGeneratorContextManager[BehaviorHandler[T]]], name: str) -> None:
        super().__init__()
        self._nursery = nursery
        self._send, self._receive = trio.open_memory_channel(0)
        self._behavior = behavior
        self._ref = LocalRef[T](self)
        self._name = name

    def ref(self) -> "Ref[T]":
        return self._ref

    def handle(self, msg: T) -> None:
        # put into channel
        self._send.se
        self._nursery.nursery.start_soon(self._send.send, msg)

    async def behavior_task(self) -> None:
        """
        The main entry point for each behavior and therefore each actor.
        This method is a single task in the trio concept.
        Everything below this Behavior happens in this task.
        """
        try:
            async with self._behavior() as b:
                while True:
                    msg = await self._receive.receive()
                    new_behavior = await b.handle(msg)
                    match new_behavior:
                        case Behaviors.Ignored:
                            print(f"Message ignored: {msg}")
                        case Behaviors.Same:
                            pass
                        case Behaviors.Stop:
                            await self.stop()
                        case BehaviorHandler():
                            b = new_behavior
        finally:
            pass


    async def stop(self) -> None:
        """
        Stops the behavior and
        """
        await self._send.aclose()


class Behaviors:
    Same: BehaviorSignal = BehaviorSignal(1)
    """
    Indicates that the Behavior should stay the same for the next message.
    """

    Stop: BehaviorSignal = BehaviorSignal(2)
    """
    Indicates that the Behavior wants to be stopped. 
    A Behavior will get a final 'Stopped' LifecycleSignal and will then be terminated.
    """

    Restart: BehaviorSignal = BehaviorSignal(3)
    """
    Indicates that a Behavior wants to be restarted. 
    That means that the Behavior receives a 'Stopped' and then 'Started' LifecycleSignal.
    Also means that the setup (if available) of the Behavior will be executed again.
    """

    Ignored: BehaviorSignal = BehaviorSignal(4)
    """
    Indicates that the message was not handled and ignored. 
    """

    @staticmethod
    def receive(func: Callable[[T], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages as well as lifecycle signals.
        """
        return BehaviorHandlerImpl(behavior=func)

    @staticmethod
    def supervise(strategy: Callable[[Exception], Awaitable[SuperviseStrategy]], behavior: Behavior[T]) -> Behavior[T]:
        # narrow class down to a BehaviorImpl
        assert isinstance(behavior, BehaviorHandler), "The supervised behavior needs to implement the BehaviorHandler"
        return SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=behavior)
