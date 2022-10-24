from typing import TypeVar
from pyctor import T, U
from pyctor.behavior import Behavior
from pyctor.props import Props
from pyctor.ref import Ref


class Spawner:
    def spawn(self, behavior: Behavior[U]) -> Ref[U]:
        pass
