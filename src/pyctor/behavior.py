from abc import ABC, abstractmethod
from asyncio import Queue
from typing import Callable, Generic, Type

from pyctor.types import T, U


class Behavior(Generic[T]):
    def handle(self, msg: T) -> None:
        pass

class ExtensibleBehavior(Behavior[T]):
    pass


class Receive(ABC, Generic[T]):
    @abstractmethod
    def receiveMessage(self, msg: T) -> Behavior[T]:
        pass


class ReceiveBuilder(Generic[T]):
    def build(self) -> Receive[T]:
        pass

    def onMessage(self, clazz: Type[U], func: Callable[[U], Behavior[T]]) -> "ReceiveBuilder[T]":
        pass


class AbstractBehavior(ABC, Behavior[T]):
    @abstractmethod
    def createReceive(self) -> Receive[T]:
        pass

    def newReceiveBuilder(self) -> ReceiveBuilder[T]:
        pass

class BehaviorImplementation(Behavior[T]):
    _queue: Queue[T]
    _behavior: Behavior[T]
    _stopped: bool = False

    def __init__(self, behavior: Behavior[T]) -> None:
        super().__init__()
        self._queue = Queue() # TODO: reference loop
        self._behavior = behavior

    def send(self, msg: T) -> None:
        self._queue.put_nowait(msg)

    async def run(self) -> None:
        while not self._stopped:
            item = await self._queue.get()
            self._behavior.handle(item)
