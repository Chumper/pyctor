from typing import Any, Generic
from pyctor import T

from pyctor.messages import Message


class Actor(Generic[T]):
    def receive(self, msg: Message[T]):
        pass
