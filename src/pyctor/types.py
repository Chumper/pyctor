from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Awaitable, Callable, Generic, List, Protocol, TypeAlias, TypeVar, overload, runtime_checkable
from uuid import UUID, uuid4

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

    async def handle(self, ctx: "Context[T]", msg: T) -> "Behavior[T]":
        """
        Whenever a new message is received by the Behavior the handle method is called.
        The returned Behavior is used to either setup the new Behavior for the next message
        or when one of the BehaviorSignals is given the state of the Behavior is adjusted.
        """
        ...


class Spawner:
    """
    A Spawner handles the spawning of new Behaviors.
    Mostly integrated into a Context.
    """

    _children: List["BehaviorProcessor"] = []
    """
    Contains the children of the context
    """

    async def spawn(self, behavior: AsyncGenerator[Behavior[str], None], name: str = str(uuid4())) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...


class Context(Spawner, Generic[T]):
    """
    A Context is given to each Behavior. A Context can be used to spawn new Behaviors or to get the own address.
    A Context will wrap a spawn action into a nursery so that child behaviors get destroyed once a behavior is stopped.
    """

    def self(self) -> "Ref[T]":
        """
        Returns the address of the Behavior belonging to this context.
        """
        ...

    def nursery(self) -> trio.Nursery:
        """
        Returns the nursery that has been started in the context of this behavior.
        It can be used to work with trio concepts.
        """
        ...


BehaviorFunction: TypeAlias = Callable[["Context[T]", T], Awaitable[Behavior[T]]]
"""
Type alias to define a function that can handle a generic message in the actor system and returns a Behavior 
"""


class BehaviorProcessor(Generic[T], ABC):
    _name: str

    def handle(self, msg: T) -> None:
        ...

    def stop(self) -> None:
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


class Dispatcher(ABC):
    async def dispatch(self, handler: BehaviorHandler[T]) -> Ref[T]:
        ...
