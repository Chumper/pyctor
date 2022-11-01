from abc import ABC, abstractmethod
from enum import Enum, EnumMeta
from typing import Awaitable, Callable, Generic, Type, TypeAlias, final, get_origin

import trio
import trio_typing

from pyctor.messages import Message, Signal
from pyctor.types import T, U


class Behavior(ABC, Generic[T]):
    pass


class LifecycleSignal(Enum):
    Started = 1
    Stopped = 2


class BehaviorHandler(Behavior[T], ABC):
    @abstractmethod
    async def _handle(self, msg: T | LifecycleSignal) -> Behavior[T]:
        pass
    async def _setup(self, ctx: 'Context[T]') -> None:
        pass


# Can't use enums...
@final
class SameBehaviorSignal(Behavior[T]):
    async def handler(self, msg: T) -> "SameBehaviorSignal":
        return self


@final
class StopBehaviorSignal(Behavior[T]):
    async def handler(self, msg: T) -> "StopBehaviorSignal":
        return self


@final
class RestartBehaviorSignal(Behavior[T]):
    async def handler(self, msg: T) -> "RestartBehaviorSignal":
        return self


class MessageBehavior(BehaviorHandler[T]):
    _message_handler: Callable[[T], Awaitable[Behavior[T]]]

    def __init__(
        self,
        message_handler: Callable[[T], Awaitable[Behavior[T]]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__()
        if message_handler:
            self._message_handler = message_handler
        else:
            self._message_handler = Behaviors.Same.handler

    async def _handle(self, msg: T | LifecycleSignal) -> "Behavior[T]":
        return await self._message_handler(msg)  # type: ignore


class SignalBehavior(Behavior[T]):
    _signal_handler: Callable[[LifecycleSignal], Awaitable["Behavior[T]"]]

    def __init__(
        self,
        signal_handler: Callable[[LifecycleSignal], Awaitable["Behavior[T]"]]
        | None = None,
        **kwargs,
    ) -> None:
        super().__init__()
        if signal_handler:
            self._signal_handler = signal_handler
        else:
            self._signal_handler = Behaviors.Same.handler

    async def _handle(self, signal: T | LifecycleSignal) -> "Behavior[T]":
        return await self._signal_handler(signal)  # type: ignore


class CompositeBehavior(Behavior[T]):
    _signal_behavior: SignalBehavior[T]
    _message_behavior: MessageBehavior[T]

    def __init__(
        self,
        signal_handler: Callable[[LifecycleSignal], Awaitable["Behavior[T]"]]
        | None = None,
        message_handler: Callable[[T], Awaitable[Behavior[T]]] | None = None,
    ) -> None:
        super().__init__()
        self._signal_behavior = SignalBehavior(signal_handler)
        self._message_behavior = MessageBehavior(message_handler)

    async def _handle(self, msg: T | LifecycleSignal) -> "Behavior[T]":
        match msg:
            case LifecycleSignal():
                return await self._signal_behavior._handle(msg)
            case _:
                return await self._message_behavior._handle(msg)


class StopBehavior(MessageBehavior[T]):
    async def _handle_message(self, msg: T) -> "Behavior[T]":
        raise Exception("Actor is stopped")


class Receive(ABC, Generic[T]):
    @abstractmethod
    def receiveMessage(self, msg: T) -> Behavior[T]:
        pass


class ReceiveBuilder(Generic[T]):
    def build(self) -> Receive[T]:  # type: ignore
        pass

    def onMessage(
        self, clazz: Type[U], func: Callable[[U], Behavior[T]]
    ) -> "ReceiveBuilder[T]":
        return self


class BehaviorBuilder(Generic[T]):
    def build(self) -> Behavior[T]:  # type: ignore
        pass

    def on_message(
        self, clazz: Type[U], func: Callable[[U], Behavior[T]]
    ) -> "BehaviorBuilder[T]":
        return self


class BehaviorImpl(Behavior[T]):
    _send: trio.abc.SendChannel[T | LifecycleSignal]
    _receive: trio.abc.ReceiveChannel[T | LifecycleSignal]
    _behavior: BehaviorHandler[T]
    _ref: 'Ref[T]'

    def __init__(
        self,
        behavior: BehaviorHandler[T],
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
        while True:
            msg = await self._receive.receive()
            # print("Got from channel")
            await self._behavior._handle(msg)


class Behaviors:

    Same: SameBehaviorSignal = SameBehaviorSignal()
    Stop: StopBehaviorSignal = StopBehaviorSignal()
    Restart: RestartBehaviorSignal = RestartBehaviorSignal()

    @staticmethod
    def setup(factory: Callable[["Context[T]"], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        The setup is run when an actor is created.
        It can be used to prepare resources that are needed before the first message arrives.
        """
        return Behaviors.Same

    @staticmethod
    def receive(func: Callable[[T], Awaitable[Behavior[T]]]) -> Behavior[T]:
        """
        Defines a Behavior that handles custom messages.
        """
        return MessageBehavior(message_handler=func)

    @staticmethod
    def receive_message(
        func: Callable[[T], Awaitable[Behavior[T]]]
    ) -> MessageBehavior[T]:
        """
        Defines a Behavior that handles custom messages and returns the next Behavior.
        """
        return MessageBehavior(message_handler=func)

    @staticmethod
    def receive_signal(
        func: Callable[[LifecycleSignal], Awaitable[SignalBehavior[T]]]
    ) -> SignalBehavior[T]:
        """
        Defines a Behavior that handles a lifecycle signal and returns a behavior
        """
        return SignalBehavior(signal_handler=func)

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


class Ref(Generic[T]):
    _impl: BehaviorImpl[T]

    def __init__(self, behavior: BehaviorImpl[T]) -> None:
        super().__init__()
        self._impl = behavior

    async def send(self, msg: T) -> None:
        await self._impl.handle(msg)


class Sender:
    def send(self, ref: Ref[T], msg: T):
        pass


class Context(Generic[T]):
    def self(self) -> Ref[T]:  # type: ignore
        pass

    def spawn(self, behavior: Behavior[T]) -> Ref[T]: # type: ignore
        pass
