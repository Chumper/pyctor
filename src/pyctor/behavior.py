from enum import Enum
from typing import Awaitable, Callable

import trio

from pyctor.context import ContextImpl
from pyctor.ref import LocalRef
from pyctor.signals import BehaviorSignal
from pyctor.types import Behavior, BehaviorFunction, BehaviorHandler, BehaviorProcessor, Context, LifecycleSignal, Ref, T


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

class LoggingBehaviorHandlerImpl(BehaviorHandler[T], Behavior[T]):
    """
    Logs every message that goes through the behavior
    """
    _behavior: BehaviorHandler[T]

    def __init__(self, behavior: Behavior[T]) -> None:
        self._behavior = behavior # type: ignore

    async def handle(self, ctx: "Context[T]", msg: T | "LifecycleSignal") -> "Behavior[T]":
        print(f"Start handling: {msg}")
        b = await self._behavior.handle(ctx=ctx, msg=msg)
        print(f"End handling: {msg}")
        return b


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
    _parent_nursery: trio.Nursery
    _own_nursery: trio.Nursery
    
    _send: trio.abc.SendChannel[T]
    _receive: trio.abc.ReceiveChannel[T]
    
    _behavior: BehaviorHandler[T]
    _ctx: Context[T]

    @staticmethod
    async def create(nursery: trio.Nursery, behavior: BehaviorHandler[T], name: str | None = None) -> Ref[T]:
        """
        Starts a new BehaviorProcessor in the given nursery, starts a new nursery for its own children.
        Returns the Ref to this Processor
        """
        # prepare everything and start the 
        b = BehaviorProcessorImpl(nursery=nursery, behavior=behavior, name=name)
        await nursery.start(b.behavior_task)
        return b.ref()

    def __init__(self, nursery: trio.Nursery, behavior: BehaviorHandler[T], name: str | None = None) -> None:
        super().__init__()
        self._parent_nursery = nursery
        self._send, self._receive = trio.open_memory_channel(0)
        self._behavior = behavior
        self._ref = LocalRef[T](self)

    def ref(self) -> 'Ref[T]':
        return self._ref
    
    def handle(self, msg: T | LifecycleSignal) -> None:
        # put into channel
        self._own_nursery.start_soon(self._send.send, msg)

    async def behavior_task(self, task_status=trio.TASK_STATUS_IGNORED) -> None:
        """
        The main entry point for each behavior and therefore each actor.
        This method is a single task in the trio concept.
        Everything below this Behavior happens in this task.
        """
        async with trio.open_nursery() as n:
            self._own_nursery = n
            self._ctx = ContextImpl(nursery=n, ref=self._ref)
            task_status.started()
            
            await self._lifecycle()

    
    async def _lifecycle(self) -> None:
        # send started signal
        self.__handle_internal(LifecycleSignal.Started)
        while True:
            msg = await self._receive.receive()
            if not self.__handle_internal(msg=msg):
                break
            

    async def __handle_internal(self, msg: T | LifecycleSignal) -> bool:
        new_behavior = await self._behavior.handle(self._ctx, msg)
        match new_behavior:
            case Behaviors.Ignored:
                print(f"Message ignored: {msg}")
            case Behaviors.Same:
                pass
            case Behaviors.Stop:
                self.stop()
            case BehaviorHandler():
                self._behavior = new_behavior
        match msg:
            case LifecycleSignal.Stopped:
                return False
        return True
            
    
    def stop(self) -> None:
        """
        Stops the behavior and handles the correct lifecycle events
        """
        # send stopping message
        self.handle(LifecycleSignal.Stopping)
        # terminate children
        for c in self._ctx._children:
            c.stop()
        # send stopping message
        self.handle(LifecycleSignal.Stopped)



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