
from typing import Any, TypeVar, Union

from pyctor.messages import SystemMessage

T = TypeVar("T")

class Actor[T]():
    def receive(msg: Union[SystemMessage, T]):
        pass
