from abc import ABC
from typing import Union

from pyctor.types import T


class Signal(ABC):
    pass


class PoisionPill(Signal):
    pass


class Started(Signal):
    pass


class Restarted(Signal):
    pass


class Stopped(Signal):
    pass


Message = Union[T, Signal]
