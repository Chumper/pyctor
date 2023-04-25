import uuid
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncContextManager,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    List,
    NotRequired,
    Optional,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    runtime_checkable,
)

import trio
from msgspec import Struct
from pydantic import BaseModel, Field

T = TypeVar("T")
"""
Generic type variable for the message type
"""

U = TypeVar("U")
"""
Generic type variable for additional message types
"""

V = TypeVar("V")
"""
Generic type variable for the reply type
"""


class BehaviorSignal(ABC):
    """
    A BehaviorSignal is used to indicate a change the state of the Behavior.
    It is an optimization to avoid the creation of new Behaviors in certain cases.
    """

    ...  # pragma: no cover


@runtime_checkable
class BehaviorFunctionHandler(Protocol[T]):
    """
    Class that all Behaviors need to implement if they want to be handled by the behavior system.
    This class fullfills the Protocol requirements needed to handle the internals.
    """

    async def handle(self, msg: T) -> "Behavior[T]":
        """
        Whenever a new message is received by the Behavior the handle method is called.
        The returned Behavior is used to setup the new Behavior for the next message
        or when one of the BehaviorSignals is returned then the state of the Behavior is adjusted.
        """
        ...  # pragma: no cover


class Context(Generic[T]):
    """
    A Context is useful for behaviors that need a reference to itself or need other functionality to interact with its own behavior.
    A Context will only be provided if the behavior is initialized with a context manager, it will then get its own context as argument
    """

    @abstractmethod
    def self(self) -> "Ref[T]":
        """
        Returns a Ref to the behavior this context belongs to.
        Can be useful if the own Ref needs to be send other behaviors (e.g. children).
        """
        ...

    @abstractmethod
    async def watch(self, ref: "Ref[U]", msg: T):
        """
        Will watch the given Ref and send the given message to the behavior
        this context belongs to when the watched Ref is terminated.

        Watching the Ref of the behavior of this context makes no sense and will
        not work because the message cannot be handled after the behavior stopped.
        """
        ...

    # @abstractmethod
    # @asynccontextmanager
    # def with_stash(self, n: int) -> AsyncGenerator["Stash[T]", None]:
    #     ...

    # @abstractmethod
    # @asynccontextmanager
    # def with_timer(self) -> AsyncGenerator["Timer", None]:
    #     ...


BehaviorGenerator: TypeAlias = AsyncContextManager[BehaviorFunctionHandler[T]]
"""
A BehaviorGenerator is a context manager that will return a BehaviorHandler.
"""

BehaviorGeneratorFunction: TypeAlias = Callable[[Context[T]], BehaviorGenerator[T]]
"""
A BehaviorGeneratorFunction is a function that takes a context and returns a BehaviorGenerator.
"""

Behavior: TypeAlias = Callable[[Context[T]], BehaviorGenerator[T]] | BehaviorSignal
"""
The base building block for everything.
A Behavior simply defines how to handle a message. 
A Behavior can return a new Behavior (or the same) for the next message.
Additionally a Behavior can return a BehaviorSignal to change the state of itself.
"""

BehaviorFunction: TypeAlias = Callable[[T], Awaitable[Behavior[T]]]
"""
A BehaviorFunction is a function that takes a message and returns a Behavior.
"""

BehaviorSetup: TypeAlias = AsyncGenerator[BehaviorGeneratorFunction[T], None]
"""	
A BehaviorSetup is a generator that will yield a BehaviorGeneratorFunction.
The BehaviorGeneratorFunction will be used to setup the behavior for the next message.
"""


class SpawnOptions(TypedDict):
    name: NotRequired[str]
    buffer_size: NotRequired[int]


class Spawner(ABC):
    """
    A Spawner handles the spawning of new Behaviors.
    Mostly integrated into a ContextManager
    """

    @abstractmethod
    async def spawn(
        self,
        behavior: BehaviorGeneratorFunction[T],
        options: SpawnOptions | None = None,
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
    def stop_all(self) -> None:
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

    registry: str
    """
    The registry that the ref belongs to. 
    It is the registry of the process that spawned the behavior.
    """
    name: str
    """
    The name of the behavior inside the registry, is unique with this registry.
    """

    def send(self, msg: T) -> None:
        """
        TBD
        """
        ...  # pragma: no cover

    def stop(self) -> None:
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


class MessageStrategy(Generic[T], ABC):
    """
    This class is used to define different send methods based on locality.
    There can be an implementation for local sending and for remote sending
    """

    @abstractmethod
    def transform_send_message(self, me: Ref[T], msg: T) -> Any:
        """
        This method will be called before a message is send to a Ref.
        """
        ...

    @abstractmethod
    def transform_stop_message(self, me: Ref[T]) -> Optional[Any]:
        """
        This method will be called before a stop message is send to a Ref.
        """
        ...


class Sender:
    """
    This class is used to send messages to a Ref.
    It is used by the Context to send messages to the behavior.
    """

    def send(self, ref: Ref[T], msg: T) -> None:
        """
        TBD
        """
        ...  # pragma: no cover

    def stop(self, ref: Ref[T]) -> None:
        """
        EXPERIMENTAL: Not sure yet if this should stay.

        Will send a system message to the behavior to stop the behavior and all of its children.
        """
        ...  # pragma: no cover

    async def ask(self, ref: Ref[T], f: Callable[["Ref[V]"], ReplyProtocol[V]]) -> V:
        """
        EXPERIMENTAL: Feedback needed

        Will send a typed message to a Ref and waits for an answer.
        Internally this will spawn a ResponseBehavior and sets the reply_to to this newly spawned behavior.
        Supports trio standard cancelation scope and should be used to place a timeout on the request.
        """
        ...  # pragma: no cover


class BehaviorNursery(Spawner):
    """
    A BehaviorNursery is a Spawner that spawns Behaviors in a nursery.
    It is used by the Context to spawn children.
    """

    _nursery: trio.Nursery


class Dispatcher(ABC):
    """
    The Dispatcher is responsible to dispatch a Behavior.
    There can be different dispatchers depending on the use case.
    Currently supported are a single process dispatcher and a multi process dispatcher.
    """

    async def dispatch(
        self, behavior: BehaviorGeneratorFunction[T], options: SpawnOptions | None
    ) -> Ref[T]:
        """
        Spawns the given behavior in a process and provides the Ref to the spawned behavior
        """
        ...  # pragma: no cover


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


class Registry:
    """
    The Registry is responsible to keep track of all the refs that are registered in the current process.
    """

    url: str
    """
    The URL of the registry
    """

    @abstractmethod
    async def watch(self, ref: Ref[T], watcher: Ref[U], msg: U) -> None:
        ...

    @abstractmethod
    async def register(self, name: str, channel: trio.abc.SendChannel[T]) -> Ref[T]:
        ...

    @abstractmethod
    async def deregister(self, ref: Ref[T]) -> None:
        ...

    @abstractmethod
    def channel_from_ref(self, ref: Ref[T]) -> trio.abc.SendChannel[T]:
        ...

    @abstractmethod
    def ref_from_raw(self, registry: str, name: str) -> Ref[T]:
        ...

    @abstractmethod
    async def register_remote(self, registry: str, ref: Ref[T]) -> None:
        ...

    @abstractmethod
    def remotes(self) -> List[trio.abc.SendChannel]:
        ...


class Timer:
    pass


class StoppedEvent(Struct, tag_field="msg_type", tag=str.lower):
    """
    This event indicates that a behavior has stopped.
    """

    ref: Ref[Any]
    """
    The ref of the stopped behavior
    """
