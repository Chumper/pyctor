from typing import Generic

from pyctor.messages import Message
from pyctor.types import T


class Actor(Generic[T]):
    def receive(self, msg: Message[T]):
        pass
