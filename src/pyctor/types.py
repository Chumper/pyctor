from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncContextManager, AsyncGenerator, Awaitable, Callable, Generic, List, Protocol, Type, TypeAlias, TypeVar, runtime_checkable
from uuid import uuid4

import trio

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


@runtime_checkable
class BehaviorHandler(Protocol[T]):
    """
    Class that all Behaviors need to implement if they want to be handled by the actor system.
    This class fullfills the Protocol requirements needed to handle the internals.
    """

    async def handle(self, msg: T) -> "Behavior[T]":
        """
        Whenever a new message is received by the Behavior the handle method is called.
        The returned Behavior is used to either setup the new Behavior for the next message
        or when one of the BehaviorSignals is given the state of the Behavior is adjusted.
        """
        ...  # pragma: no cover


class BehaviorSignal(ABC):
    ...  # pragma: no cover


class Context(Generic[T]):
    @abstractmethod
    def self(self) -> "Ref[T]":
        ...

    # @abstractmethod
    # @asynccontextmanager
    # def with_stash(self, n: int) -> AsyncGenerator["Stash[T]", None]:
    #     ...

    # @abstractmethod
    # @asynccontextmanager
    # def with_timer(self) -> AsyncGenerator["Timer", None]:
    #     ...


BehaviorGenerator: TypeAlias = AsyncContextManager[BehaviorHandler[T]]
"""
A ContextManager that will yield a BehaviorHandler that can be used to handle messages
"""

BehaviorGeneratorFunction: TypeAlias = Callable[[Context[T]], BehaviorGenerator[T]]

Behavior: TypeAlias = Callable[[Context[T]], BehaviorGenerator[T]] | BehaviorSignal
"""
The basic building block of everything.
A Behavior defines how an actor will handle a message and will return a Behavior for the next message.
"""

BehaviorFunction: TypeAlias = Callable[[T], Awaitable[Behavior[T]]]
"""
Type alias to define a function that can handle a generic message and returns a Behavior 
"""

BehaviorSetup: TypeAlias = AsyncGenerator[BehaviorGeneratorFunction[T], None]


class Spawner(ABC):
    """
    A Spawner handles the spawning of new Behaviors.
    Mostly integrated into a ContextManager
    """

    @abstractmethod
    async def spawn(
        self,
        behavior: BehaviorGeneratorFunction[T],
        name: str | None = None,
    ) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...  # pragma: no cover

    @abstractmethod
    def children(self) -> List["Ref[None]"]:
        """
        Returns a list of children, which means that those are
        behavior tasks that have been spawned by this Spawner
        """
        ...  # pragma: no cover

    @abstractmethod
    async def stop(self) -> None:
        """
        Will stop all children that have been spawned by this nursery.
        """
        ...  # pragma: no cover


class BehaviorProcessor(Protocol):
    async def behavior_task(self):
        ...  # pragma: no cover


class ReplyProtocol(Protocol[V]):
    """
    Defines the interface that is needed if the ask pattern is being used with the system.
    Every message requires a reply_to ref so that typing can infer the types.
    """

    reply_to: "Ref[V]"
    """
    The typed Ref that should receive the response (if any)
    """


class Ref(Generic[T], ABC):
    """
    A Ref always points to an instance of a Behavior.
    The ref is used to send messages to the Behavior.
    """

    url: str
    """
    Contains the URL of this behavior
    """

    def send(self, msg: T) -> None:
        """
        TBD
        """
        ...  # pragma: no cover

    async def stop(self) -> None:
        """
        EXPERIMENTAL: Not sure yet if this should stay.

        Will send a system message to the behavior to stop the behavior and all of its children.
        """
        ...  # pragma: no cover

    async def ask(self, f: Callable[["Ref[V]"], ReplyProtocol[V]]) -> V:
        """
        EXPERIMENTAL: Feedback needed

        Will send a typed message to a Ref and waits for an answer.
        Internally this will spawn a ResponseBehavior and sets the reply_to to this newly spawned behavior.
        Supports trio standard cancelation scope and should be used to place a timeout on the request.
        """
        ...  # pragma: no cover

    def unsafe_cast(self, clazz: Type[U]) -> "Ref[U]":
        ...  # pragma: no cover


class BehaviorNursery(Spawner):
    _nursery: trio.Nursery


class Dispatcher(ABC):
    """
    The Dispatcher is responsible to dispatch a Behavior...
    """

    async def dispatch(
        self,
        behavior: BehaviorGeneratorFunction[T],
        name: str,
    ) -> Ref[T]:
        ...  # pragma: no cover


@dataclass
class BehaviorNurseryOptions:
    dispatcher: Dispatcher


class Stash(Generic[T], ABC):
    @abstractmethod
    async def stash(self, msg: T) -> None:
        ...  # pragma: no cover

    @abstractmethod
    async def unstash(self, amount: int) -> List[T]:
        ...  # pragma: no cover

    @abstractmethod
    async def close(self) -> None:
        ...  # pragma: no cover


class Timer:
    pass
