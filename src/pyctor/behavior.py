from abc import ABC, abstractmethod
from typing import Callable, Generic, Type

from pyctor import T, U


class Behavior(Generic[T]):
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
