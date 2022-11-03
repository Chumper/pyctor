from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Generic, TypeAlias

import trio

from pyctor.types import T


class LifecycleSignal(Enum):
    """
    A LifecycleSignal is send to a Behavior to indicate the phases a Behavior can go through.
    When a Behavior is started, the first LifecycleSignal it will get will be 'Started'.
    When a Behavior is stopped, the last LifecycleSignal will be 'Stopped'.

    A LifecycleSignal can be used to do certain actions that are required during the lifecycle.
    """

    Started = 1
    Stopped = 2


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

    def __init__(
        self,
        behavior: BehaviorImpl[T],
    ) -> None:
        super().__init__()
        self._send, self._receive = trio.open_memory_channel(0)
        self._behavior = behavior
        self._ref = Ref(self)

    async def handle(self, msg: T | LifecycleSignal) -> None:
        # put into channel
        # print("Put into channel")
        await self._send.send(msg)

    async def behavior_task(self):
        # call setup method
        await self._behavior.setup(None)  # type: ignore
        await self._behavior.handle(None, LifecycleSignal.Started)  # type: ignore
        try:
            while True:
                msg = await self._receive.receive()
                # print("Got from channel")
                await self._behavior.handle(None, msg)  # type: ignore
        finally:
            await self._behavior.handle(None, LifecycleSignal.Stopped)  # type: ignore
        

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
    Indicates that the Behavior wants to be stopped. A Behavior will get a final 'Stopped' LifecycleSignal and will then be terminated.
    """

    Restart: BehaviorSignal = BehaviorSignal(3)
    """
    Indicates that a Behavior wants to be restarted. That means that the Behavior receives a 'Stopped' and then 'Started' LifecycleSignal.
    Also means that the setup (if available) of the Behavior will be executed again.
    """

    @staticmethod
    def setup(factory: Callable[["Context[T]"], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        The setup is run when an actor is created.
        It can be used to prepare resources that are needed before the first message arrives.
        """
        # return BehaviorHandlerImpl()
        return Behaviors.Same

    @staticmethod
    def receive(func: Callable[[T | LifecycleSignal], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages.
        """

        # Define an outer setup handler that just returns the provided func
        async def receive_setup(ctx: "Context[T]") -> BehaviorHandler[T]:
            async def receive_handler(
                ctx: "Context[T]", msg: T | LifecycleSignal
            ) -> Behavior[T]:
                # as all messages are handled there is no need to configure anything here
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


class Context(Generic[T]):
    def self(self) -> "Ref[T]":  # type: ignore
        pass

    def spawn(self, behavior: Behavior[T]) -> "Ref[T]":  # type: ignore
        pass


class Ref(Generic[T]):
    _impl: BehaviorProcessor[T]

    def __init__(self, behavior: BehaviorProcessor[T]) -> None:
        super().__init__()
        self._impl = behavior

    async def send(self, msg: T) -> None:
        await self._impl.handle(msg)
