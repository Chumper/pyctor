from typing import TypeVar

from pyctor.props import Props
from pyctor.ref import Ref

T = TypeVar("T")

class Spawner():
    def spawn(props: Props[T]) -> Ref[T]:
        pass

class Sender():
    def send(ref: Ref[T], msg: T):
        pass

class ActorSystem(Spawner, Sender):
    pass
