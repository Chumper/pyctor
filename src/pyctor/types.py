from abc import ABC, abstractmethod
from contextlib import _AsyncGeneratorContextManager
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    List,
    Protocol,
    Type,
    TypeAlias,
    TypeVar,
    get_args,
    overload,
    runtime_checkable,
)
from uuid import uuid4

import trio

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class Behavior(ABC, Generic[T]):
    """
    The basic building block of everything in Pyctor.
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
        behavior: Behavior[T]
        | Callable[[], _AsyncGeneratorContextManager[Behavior[T]]],
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
        Will stop all children.
        """
        ...

BehaviorFunction: TypeAlias = Callable[[T], Awaitable[Behavior[T]]]
"""
Type alias to define a function that can handle a generic message in the actor system and returns a Behavior 
"""


class BehaviorProcessor(Generic[T], ABC):
    _name: str
    _type_T: Any

    def __init_subclass__(cls) -> None:
        cls._type_T = get_args(cls.__orig_bases__[0])[0]  # type: ignore

    async def handle(self, msg: T) -> None:
        ...

    def handle_nowait(self, msg: T) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def behavior_task(self):
        ...

    def ref(self) -> "Ref[T]":
        ...


class ReplyProtocol(Protocol[T]):
    """
    Defines the interface that is needed if the ask pattern is being used with pyctor.
    Every message requires a reply_to ref so that typing can interfer the types.
    """

    reply_to: "Ref[T]"
    """
    The typed Ref that should receive the response (if any)
    """


class Actor(Generic[T], ABC):
    """
    OOP part of Pyctor. A class needs to implement the Actor interface to be scheduled.
    It is not nessesarly needed, but gives developers guidance on what to provide.
    """

    def create(self) -> Behavior[T]:
        """
        Static function that will return a Behavior from an actor.
        This method is the main entry point into the actor system for the actor class.
        """
        ...


class Ref(Generic[T], ABC):
    """
    A Ref always points to an instance of a Behavior.
    The ref is used to send messages to the Behavior.
    """

    async def send(self, msg: T) -> None:
        """
        TBD
        """
        ...

    def send_nowait(self, msg: T) -> None:
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

    def stop_nowait(self) -> None:
        """
        EXPERIMENTAL: Not sure yet if this should stay.

        Will send a system message to the behavior to stop the behavior and all of its children.
        """
        ...

    async def ask(self, msg: ReplyProtocol[V]) -> V:
        """
        EXPERIMENTAL: Not sure yet if this should stay.

        Will send a typed message to a Ref and waits for an answer.
        Internally this will spawn a ResponseBehavior and sets the reply_to to this newly spawned behavior.
        Supports trio standard cancelation scope and should be used to place a timeout on the request.
        """
        ...

    def address(self) -> str:
        """
        Will return the address of this Behavior
        """
        ...

    def unsafe_cast(self, clazz: Type[U]) -> "Ref[U]":
        ...


class ActorNursery(Spawner):
    pass


class Dispatcher(ABC):
    async def dispatch(self, handler: BehaviorHandler[T]) -> Ref[T]:
        ...
