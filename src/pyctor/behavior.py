from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Generic, List, Protocol, TypeAlias

import trio
from typing_extensions import reveal_type

from pyctor.types import T


class LifecycleSignal(Enum):
    """
    A LifecycleSignal is send to a Behavior to indicate the phases a Behavior can go through.
    When a Behavior is started, the first LifecycleSignal it will get will be 'Started'.
    When a Behavior is stopped, the last LifecycleSignal will be 'Stopped'.

    A LifecycleSignal can be used to do certain actions that are required during the lifecycle.
    """

    Started = 1
    """
    Wil be sent once a behavior is started
    """

    Stopped = 2
    """
    Will be sent once a behavior is stopped and after all it's children are stopped.
    After the message is handled a behavior is terminated
    """


class Behavior(ABC, Generic[T]):
    """
    The basic building block of everything in Pyctor.
    A Behavior defines how an actor will handle a message and will return a Behavior for the next message.
    """
    ...


BehaviorHandler: TypeAlias = Callable[
    ["Context[T]", T | LifecycleSignal], Awaitable[Behavior[T]]
]

@dataclass
class BehaviorSignal(Behavior[T]):
    """
    A class to house all BehaviorSignal that can be returned by a Behavior
    The index is used to differentiate the different signals
    """
    __index: int


class BehaviorImpl(Behavior[T]):
    """
    Class that all Behaviors need to implement if they want to be handled by Pyctor.
    This class fullfills the Protocol requirements.
    """

    _func: Callable[["Context[T]"], Awaitable[BehaviorHandler[T]]]
    _behavior: BehaviorHandler[T]

    def __init__(
        self, func: Callable[["Context[T]"], Awaitable[BehaviorHandler[T]]]
    ) -> None:
        self._func = func

    async def setup(self, ctx: "Context[T]") -> None:
        self._behavior = await self._func(ctx)

    async def handle(
        self, ctx: "Context[T]", msg: T | LifecycleSignal
    ) -> "Behavior[T]":
        return await self._behavior(ctx, msg)


# class StopBehavior(BehaviorHandlerImpl[T]):
#     def __init__(self, handler: Callable[['Context[T]'], BehaviorHandler[T]]) -> None:
#         def stop_behavior(ctx: 'Context[T]') -> BehaviorHandler[T]:
#             return class:
#             pass
#         super().__init__(stop_behavior)

#     async def _handle_message(self, msg: T) -> "Behavior[T]":
#         raise Exception("Actor is stopped")


# class Receive(ABC, Generic[T]):
#     @abstractmethod
#     def receiveMessage(self, msg: T) -> Behavior[T]:
#         pass


# class ReceiveBuilder(Generic[T]):
#     def build(self) -> Receive[T]:  # type: ignore
#         pass

#     def onMessage(
#         self, clazz: Type[U], func: Callable[[U], Behavior[T]]
#     ) -> "ReceiveBuilder[T]":
#         return self


# class BehaviorBuilder(Generic[T]):
#     def build(self) -> Behavior[T]:  # type: ignore
#         pass

#     def on_message(
#         self, clazz: Type[U], func: Callable[[U], Behavior[T]]
#     ) -> "BehaviorBuilder[T]":
#         return self


class BehaviorProcessor(Generic[T]):
    _send: trio.abc.SendChannel[T | LifecycleSignal]
    _receive: trio.abc.ReceiveChannel[T | LifecycleSignal]
    _behavior: BehaviorImpl[T]
    _ref: "Ref[T]"
    _ctx: 'Context[T]'
    _stopped: bool = False

    def __init__(
        self,
        behavior: BehaviorImpl[T],
        name: str | None = None
    ) -> None:
        super().__init__()
        self._send, self._receive = trio.open_memory_channel(0)
        self._behavior = behavior
        self._ref = Ref[T](self)


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
            ctx = Context(nursery=n)

            # call setup method
            await self._behavior.setup(ctx)
            # print(reveal_type(self._behavior))
            await self._behavior.handle(ctx, LifecycleSignal.Started)
            try:
                while not self._stopped:
                    msg = await self._receive.receive()
                    match msg:
                        case LifecycleSignal.Stopped: 
                            self._stopped = True
                            for c in ctx._children:
                                await c.send(LifecycleSignal.Stopped)

                    # print("Got from channel")
                    new_behavior = await self._behavior.handle(ctx, msg)
                    match new_behavior:
                        case Behaviors.Same:
                            pass
                        case BehaviorImpl():
                            self._behavior = new_behavior
                            await self._behavior.setup(ctx)
                        case _:
                            raise Exception(f"Behavior cannot be handled: {new_behavior}")
            finally:
                pass

# class InterceptorProtocol(Generic[T]):
#     pass


# class BehaviorSignalInterceptor(InterceptorProtocol[T]):
#     pass


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

    @staticmethod
    def setup(factory: Callable[["Context[T]"], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        The setup is run when an actor is created.
        It can be used to prepare resources that are needed before the first message arrives.
        """
        return BehaviorImpl(func=factory) # type: ignore
        

    @staticmethod
    def receive(
        func: Callable[[T | LifecycleSignal], Awaitable[Behavior[T]]]
    ) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages.
        """

        # Define an outer setup handler that just returns the provided func
        async def receive_setup(ctx: "Context[T]") -> BehaviorHandler[T]:
            async def receive_handler(
                ctx: "Context[T]", msg: T | LifecycleSignal
            ) -> Behavior[T]:
                # as all messages are handled there is no need to configure anything here
                reveal_type(msg)
                return await func(msg)

            return receive_handler

        return BehaviorImpl(func=receive_setup)

    @staticmethod
    def receive_message(func: Callable[[T], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages and returns the next Behavior.
        """

        async def receive_setup(ctx: "Context[T]") -> BehaviorHandler[T]:
            async def receive_handler(
                ctx: "Context[T]", msg: T | LifecycleSignal
            ) -> Behavior[T]:
                # only T messages are handled here, so match on that
                reveal_type(msg)
                match msg:
                    case LifecycleSignal():
                        return Behaviors.Same
                    case _:
                        return await func(msg)

            return receive_handler

        return BehaviorImpl(func=receive_setup)

    @staticmethod
    def receive_signal(
        func: Callable[[LifecycleSignal], Awaitable[Behavior[T]]]
    ) -> Behavior[T]:
        """
        Defines a Behavior that handles a lifecycle signal and returns a behavior
        """

        async def receive_setup(ctx: "Context[T]") -> BehaviorHandler[T]:
            async def receive_handler(
                ctx: "Context[T]", msg: T | LifecycleSignal
            ) -> Behavior[T]:
                reveal_type(msg)
                match msg:
                    case LifecycleSignal():
                        return await func(msg)
                    case _:
                        return Behaviors.Same

            return receive_handler

        return BehaviorImpl(func=receive_setup)

    # @staticmethod
    # def receive_context(func: Callable[[Context, Message[T]], Behavior[T]]) -> None:
    #     pass

    # @staticmethod
    # def fromCallable(func: Handler[T]) -> Behavior[T]:
    #     return Behaviors.Same

    # @staticmethod
    # def fromBehavior(func: AbstractBehavior[T]) -> Behavior[T]:
    #     return Behaviors.Same

    # @staticmethod
    # def fromProducer(func: Producer[T]) -> Behavior[T]:
    #     return Behaviors.Same


# class Sender:
#     def send(self, ref: 'Ref[T]', msg: T):
#         pass


class SpawnMixin(Generic[T]):
    _children: List["Ref[LifecycleSignal]"] = []
    _nursery: trio.Nursery
    
    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self._nursery = nursery

    async def spawn(self, behavior: Behavior[T]) -> "Ref[T]":
        # narrow class down to a BehaviorProtocol
        assert isinstance(behavior, BehaviorImpl), "behavior needs to implement the BehaviorProtocol"
        # create the process
        b = BehaviorProcessor(behavior=behavior)
        # start in the nursery
        self._nursery.start_soon(b.behavior_task)
        # append to array
        self._children.append(b._ref)
        # return the ref
        return b._ref

class Context(SpawnMixin[T], Generic[T]):
    """
    A Context is given to each Behavior. A Context can be used to spawn new Behaviors or to get the own address.
    A Context will wrap a spawn action into a nursery so that child behaviors get destroyed once a behavior is stopped.
    """

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__(nursery)

    def self(self) -> "Ref[T]":  # type: ignore
        pass


class Ref(Generic[T]):
    _impl: BehaviorProcessor[T]

    def __init__(self, behavior: BehaviorProcessor[T]) -> None:
        super().__init__()
        self._impl = behavior

    async def send(self, msg: T) -> None:
        await self._impl.handle(msg)


class Actor(Generic[T], ABC):
    def create(self) -> Behavior[T]:
        ...


class ReplyProtocol(Protocol[T]):
    reply_to: 'Ref[T]'
