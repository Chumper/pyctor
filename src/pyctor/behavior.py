from enum import Enum
from typing import Awaitable, Callable

import trio
from pyctor.context import ContextImpl
from pyctor.ref import LocalRef
from pyctor.signals import BehaviorSignal

from pyctor.types import (
    T,
    Behavior,
    BehaviorFunction,
    BehaviorHandler,
    BehaviorProcessor,
    Context,
    LifecycleSignal,
    Ref,
)


class BehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Class that all Behaviors need to implement if they want to be handled by Pyctor.
    This class fullfills the Protocol requirements.
    """

    _behavior: BehaviorFunction[T]

    def __init__(self, behavior: BehaviorFunction[T]) -> None:
        self._behavior = behavior

    async def handle(self, ctx: Context[T], msg: T | LifecycleSignal) -> Behavior[T]:
        return await self._behavior(ctx, msg)


class DeferredBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Will take a function that returns a BehaviorFunction.
    Can be used to set up the Behavior before accepting messages.
    """

    _func: Callable[[Context[T]], Awaitable[Behavior[T]]]
    _behavior: BehaviorHandler[T] | None = None

    def __init__(self, func: Callable[[Context[T]], Awaitable[Behavior[T]]]) -> None:
        self._func = func

    async def setup(self, ctx: Context[T]) -> Behavior[T]:
        return await self._func(ctx)

    async def handle(self, ctx: Context[T], msg: T | LifecycleSignal) -> Behavior[T]:
        if not self._behavior:
            # not set up yet, so do it now
            behavior = await self.setup(ctx)
            assert isinstance(
                behavior, BehaviorHandler
            ), "Returned behavior of a set up calls needs to be an actual behavior"
            self._behavior = behavior
        return await self._behavior.handle(ctx, msg)


class MessageBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Will only handle messages of type T and sends the messages to the BehaviorFunction
    """

    _behavior: Callable[[T], Awaitable[Behavior[T]]]

    def __init__(self, behavior: Callable[[T], Awaitable[Behavior[T]]]) -> None:
        self._behavior = behavior

    async def handle(self, ctx: Context[T], msg: T | LifecycleSignal) -> "Behavior[T]":
        if isinstance(msg, LifecycleSignal):
            return Behaviors.Same
        # we cannot guarantee that the message is of type T here, sorry...
        return await self._behavior(msg)


class SignalBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Will only handle messages of type LifecycleSignal and sends the messages to the BehaviorFunction
    """

    _behavior: Callable[[LifecycleSignal], Awaitable[Behavior[T]]]

    def __init__(
        self, behavior: Callable[[LifecycleSignal], Awaitable[Behavior[T]]]
    ) -> None:
        self._behavior = behavior

    async def handle(self, ctx: Context[T], msg: T | LifecycleSignal) -> Behavior[T]:
        if isinstance(msg, LifecycleSignal):
            return await self._behavior(msg)
        return Behaviors.Same


class SuperviseStrategy(Enum):
    Restart = 1
    Stop = 2
    Ignore = 3

class SuperviseBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Will wrap a BehaviorHandler in a supervise strategy
    """
    _strategy: Callable[[Exception], Awaitable[SuperviseStrategy]]
    _behavior: BehaviorHandler[T]

    def __init__(
        self, 
        strategy: Callable[[Exception], Awaitable[SuperviseStrategy]],
        behavior: BehaviorHandler[T]
    ) -> None:
        self._strategy = strategy
        self._behavior = behavior

    async def handle(self, ctx: Context[T], msg: T | LifecycleSignal) -> Behavior[T]:  # type: ignore
        try:
            return await self._behavior.handle(ctx, msg)
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
    _send: trio.abc.SendChannel[T | LifecycleSignal]
    _receive: trio.abc.ReceiveChannel[T | LifecycleSignal]
    _behavior: BehaviorHandler[T]
    _ref: Ref[T]
    _ctx: Context[T]
    _stopped: bool = False

    def __init__(self, behavior: BehaviorHandler[T], name: str | None = None) -> None:
        super().__init__()
        self._send, self._receive = trio.open_memory_channel(0)
        self._behavior = behavior
        self._ref = LocalRef[T](self)

        class InnerControl:
            def stop(_) -> None:
                self._stopped = True

            def set(_, b: BehaviorHandler[T]) -> None:
                self._behavior = b

        self._control = InnerControl()

    async def handle(self, msg: T | LifecycleSignal) -> None:
        # put into channel
        # print("Put into channel")
        await self._send.send(msg)

    async def behavior_task(self):
        """
        The main entry point for each behavior and therefore each actor.
        This method is a single task in the trio concept.
        Everything below this Behavior happens in this task.
        """
        async with trio.open_nursery() as n:
            ctx = ContextImpl(nursery=n)

            # print(reveal_type(self._behavior))
            await self._behavior.handle(ctx, LifecycleSignal.Started)
            while not self._stopped:
                msg = await self._receive.receive()
                # self._behavior = await self._behavior.handle(ctx, msg)

                match msg:
                    case LifecycleSignal.Stopped:
                        self._stopped = True
                        for c in ctx._children:
                            await c.handle(LifecycleSignal.Stopped)

                # print("Got from channel")
                new_behavior = await self._behavior.handle(ctx, msg)
                match new_behavior:
                    case Behaviors.Same:
                        pass
                    case BehaviorHandlerImpl():
                        self._behavior = new_behavior
                    case _:
                        raise Exception(
                            f"Behavior cannot be handled: {new_behavior}"
                        )

    def ref(self) -> Ref[T]:
        return self._ref


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
    def setup(factory: Callable[[Context[T]], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        The setup is run when an actor is created.
        It can be used to prepare resources that are needed before the first message arrives.
        """
        return DeferredBehaviorHandlerImpl(func=factory)

    @staticmethod
    def receive(
        func: Callable[[Context[T], T | LifecycleSignal], Awaitable[Behavior[T]]]
    ) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages as well as lifecycle signals.
        """
        return BehaviorHandlerImpl(behavior=func)

    @staticmethod
    def receive_message(func: Callable[[T], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages and returns the next Behavior.
        """
        return MessageBehaviorHandlerImpl(behavior=func)

    @staticmethod
    def receive_signal(
        func: Callable[[LifecycleSignal], Awaitable[Behavior[T]]]
    ) -> Behavior[T]:
        """
        Defines a Behavior that handles a lifecycle signal and returns a behavior
        """
        return SignalBehaviorHandlerImpl(behavior=func)

    @staticmethod
    def supervise(
        strategy: Callable[[Exception], Awaitable[SuperviseStrategy]],
        behavior: Behavior[T]
    ) -> Behavior[T]:
        # narrow class down to a BehaviorImpl
        assert isinstance(behavior, BehaviorHandler), "The supervised behavior needs to implement the BehaviorHandler"
        return SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=behavior)