from abc import ABC
from enum import Enum
from typing import Awaitable, Callable, Generic, List, Protocol, TypeAlias, TypeVar, runtime_checkable

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
    async def handle(
        self, ctx: "Context[T]", msg: T | "LifecycleSignal"
    ) -> "Behavior[T]":
        """
        Whenever a new message is received by the Behavior the handle method is called.
        The returned Behavior is used to either setup the new Behavior for the next message
        or when one of the BehaviorSignals is given the state of the Behavior is adjusted.
        """
        ...


class LifecycleSignal(Enum):
    """
    A LifecycleSignal is send to a Behavior to indicate the phases a Behavior can go through.
    When a Behavior is started, the first LifecycleSignal it will get will be 'Started'.
    When a Behavior is requested to stop, the LifecycleSignal will be 'Stopping'.
    When a Behavior is stopped, the last LifecycleSignal will be 'Stopped'.

    A LifecycleSignal can be used to do certain actions that are required during the lifecycle.
    """

    Started = 1
    """
    Wil be sent once a behavior is started
    """

    Stopping = 2
    """
    Will be sent once a behavior is asked to stop itself.
    After the message is handled all child behavior will receive a Stopping message as well.
    """

    Stopped = 3
    """
    Will be sent once a behavior is stopped and after all it's children are stopped.
    After the message is handled a behavior is terminated
    """


class Spawner(Generic[T]):
    """
    A Spawner handles the spawning of new Behaviors.
    Mostly integrated into a Context.
    """

    _children: List['BehaviorProcessor'] = []
    """
    Contains the children of the context
    """
    
    async def spawn(self, behavior: Behavior[T]) -> "Ref[T]":
        """
        Will spawn the given Behavior in the context of the integrated class.
        In most cases will spawn a child actor in the context of another actor.
        """
        ...


class Context(Spawner[T], Generic[T]):
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


BehaviorFunction: TypeAlias = Callable[
    ["Context[T]", T | LifecycleSignal], Awaitable[Behavior[T]]
]
"""
Type alias to define a function that can handle a generic message in the actor system and returns a Behavior 
"""

class BehaviorProcessor(Generic[T], ABC):

    def handle(self, msg: T) -> None:
        ...

    def stop(self) -> None:
        ...

    async def behavior_task(self):
        ...

    def ref(self) -> 'Ref[T]':
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

    def send(self, msg: T) -> None:
        """
        Sends a typed message to the behavior and waits until the message has been delivered.
        If it does not matter if the message reaches the sender, then do not await this method.
        """
        ...
    
    def stop(self) -> None:
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