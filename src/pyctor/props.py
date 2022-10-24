from typing import Callable, Generic, TypeAlias
from pyctor import T

from pyctor.actor import Actor
from pyctor.context import Context
from pyctor.messages import Message


Producer: TypeAlias = Callable[[], Actor[T]]
Handler: TypeAlias = Callable[[Context, Message[T]], None]

class Props(Generic[T]):
    _producer: Producer

    def __init__(self, p: Producer) -> None:
        self._producer = p


def fromCallable(func: Handler[T]) -> Props[T]:
    pass


def fromProducer(func: Producer[T]) -> Props[T]:
    return Props(func)
