
from dataclasses import dataclass

from pyctor.types import T, Behavior


@dataclass
class BehaviorSignal(Behavior[T]):
    """
    A class to house all BehaviorSignal that can be returned by a Behavior
    """

    __index: int
    """
    The index is used to differentiate the different signals like Started, Stopped, etc
    """