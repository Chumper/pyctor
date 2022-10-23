
from typing import Callable, TypeVar, Union

from pyctor.actor import Actor
from pyctor.messages import SystemMessage

T = TypeVar("T")

class Props[T]:
    pass

def fromCallable(func: Callable[[Union[SystemMessage, T]],None]) -> Props[T]:
    pass

def fromProducer(func: Callable[[],Actor[T]]) -> Props[T]:
    pass
