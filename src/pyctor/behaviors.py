from typing import Callable

from pyctor.behavior import AbstractBehavior, Behavior
from pyctor.context import Context
from pyctor.messages import Message
from pyctor.props import Handler, Producer
from pyctor.types import T


class Behaviors:
    @staticmethod
    def setup(factory: Callable[[Context[T]], Behavior[T]]) -> Behavior[T]:
        pass

    @staticmethod
    def receive(func: Callable[[Context, Message[T]], Behavior[T]]) -> None:
        pass

    @staticmethod
    def fromCallable(func: Handler[T]) -> Behavior[T]:
        pass

    @staticmethod
    def fromBehavior(func: AbstractBehavior[T]) -> Behavior[T]:
        pass

    @staticmethod
    def fromProducer(func: Producer[T]) -> Behavior[T]:
        pass
