from abc import ABC, abstractmethod
from contextlib import _AsyncGeneratorContextManager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, List, Protocol, Type, TypeAlias, TypeVar, get_args, overload, runtime_checkable
from uuid import uuid4

import trio

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class Behavior(ABC, Generic[T]):
    """
    The basic building block of everything.
    A Behavior defines how an actor will handle a message and will return a Behavior for the next message.
    """

    ...


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
        ...


class Spawner(ABC):
    """
    A Spawner handles the spawning of new Behaviors.
    Mostly integrated into a ContextManager
    """

    @overload
    @abstractmethod
    async def spawn(
        self,
        behavior: Callable[[], _AsyncGeneratorContextManager[Behavior[T]]],
        name: str = str(uuid4()),
    ) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...

    @overload
    @abstractmethod
    async def spawn(self, behavior: Behavior[T], name: str = str(uuid4())) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...

    @abstractmethod
    async def spawn(
        self,
        behavior: Behavior[T] | Callable[[], _AsyncGeneratorContextManager[Behavior[T]]],
        name: str = str(uuid4()),
    ) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...

    @abstractmethod
    def children(self) -> List["Ref[None]"]:
        """
        Returns a list of children, which means that those are
        behavior tasks that have been spawned by this Spawner
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Will stop all children that have been spawned by this nursery.
        """
        ...


BehaviorFunction: TypeAlias = Callable[[T], Awaitable[Behavior[T]]]
"""
Type alias to define a function that can handle a generic message in the actor system and returns a Behavior 
"""


class BehaviorProcessor(Protocol):
    async def behavior_task(self):
        ...


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
        ...

    async def stop(self) -> None:
        """
        EXPERIMENTAL: Not sure yet if this should stay.

        Will send a system message to the behavior to stop the behavior and all of its children.
        """
        ...

    async def ask(self, f: Callable[["Ref[V]"], ReplyProtocol[V]]) -> V:
        """
        EXPERIMENTAL: Feedback needed

        Will send a typed message to a Ref and waits for an answer.
        Internally this will spawn a ResponseBehavior and sets the reply_to to this newly spawned behavior.
        Supports trio standard cancelation scope and should be used to place a timeout on the request.
        """
        ...

    def unsafe_cast(self, clazz: Type[U]) -> "Ref[U]":
        ...


class BehaviorNursery(Spawner):
    _nursery: trio.Nursery


class Dispatcher(ABC):
    """
    The Dispatcher is responsible to dispatch a Behavior...
    """

    async def dispatch(
        self,
        behavior: Callable[
            [],
            _AsyncGeneratorContextManager[BehaviorHandler[T]],
        ],
        name: str,
    ) -> Ref[T]:
        ...


@dataclass
class BehaviorNurseryOptions:
    dispatcher: Dispatcher | None = None
