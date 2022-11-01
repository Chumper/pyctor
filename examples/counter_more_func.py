
from dataclasses import dataclass
from pyctor.behavior import Behavior, Behaviors, Ref
from pyctor.messages import Message

class Command:
    pass

class Increment(Command):
    pass

@dataclass
class GetValue(Command):
    reply_to: Ref[int]


class Counter:
    @staticmethod
    def create() -> Behavior[Command]:
        return Counter()._counter(0)

    def _counter(self, n: int) -> Behavior[Command]:
        def receive(msg: Message[Command]) -> Behavior[Command]:
            match msg:
                case Increment():
                    new_value = n + 1
                    print(f"Increment counter to {new_value}")
                    return self._counter(new_value)
                case GetValue(reply_to):
                    reply_to.send(n)
                    return Behaviors.Same
            return Behaviors.Same
        return Behaviors.receive(receive)