from dataclasses import dataclass
from typing import Any

import pyctor.types


@dataclass
class BehaviorSignal(pyctor.types.Behavior[Any]):
    """
    A class to house all BehaviorSignal that can be returned by a Behavior
    """

    __index: int
    """
    The index is used to differentiate the different signals like Started, Stopped, etc
    """
