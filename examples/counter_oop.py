from dataclasses import dataclass

import trio
import pyctor
from pyctor.behavior import Actor, Behavior, Behaviors, Ref
from pyctor.messages import Message


class Command:
    pass


class Increment(Command):
    pass


@dataclass
class GetValue(Command):
    reply_to: Ref[int]


class Counter(Actor[Command]):
    _value: int = 0

    def create(self) -> Behavior[Command]:
        return Behaviors.receive_message(self.receive)

    async def receive(self, msg: Command) -> Behavior[Command]:
        match msg:
            case Increment():
                self._value += 1
                print(f"Increment counter to {self._value}")
            case GetValue(reply_to):
                await reply_to.send(self._value)
        return Behaviors.Same


async def main() -> None:
    print("Actor System is starting up")

    async with pyctor.actor_system(Counter().create()) as asystem:
        await asystem.root().send(Increment())
        await asystem.root().send(Increment())
        # await asystem.root().send(GetValue(reply_to=))
        await asystem.root().send(Increment())

        # stop the system, otherwise actors will stay alive forever
        asystem.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
