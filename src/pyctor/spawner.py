from pyctor.behavior import Behavior
from pyctor.ref import Ref
from pyctor.types import U


class Spawner:
    def spawn(self, behavior: Behavior[U]) -> Ref[U]:
        pass
