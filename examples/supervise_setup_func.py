from contextlib import asynccontextmanager
from typing import AsyncGenerator
import trio

import pyctor
from pyctor import Behavior, Behaviors
from pyctor.signals import BehaviorSignal

"""
Simple functional example how to spawn an actor that will print messages
"""


@asynccontextmanager
async def root_setup() -> AsyncGenerator[Behavior[str], None]:
    # setup
    print("Hi from parent behavior setup")

    async def parent_handler(msg: str) -> Behavior[str]:
        print(f"parent behavior received: {msg}")
        return Behaviors.Same

    # yield root behavior
    yield Behaviors.receive(parent_handler, type_check=str)

    # teardown
    print("Hi from parent behavior teardown")


async def exception_handler(error: Exception) -> BehaviorSignal:
    match error:
        case ValueError():
            print(f"Restarting due to error: {error}")
            return Behaviors.Restart
        case _:
            print(f"Ignoring error: {error}")
            return Behaviors.Ignore


async def main() -> None:
    print("Actor System is starting up")
    supervise_behavior = Behaviors.supervise(exception_handler, root_behavior)

    async with pyctor.open_nursery() as n:
        ref = await n.spawn(root_setup)

        with trio.move_on_after(1) as cs:
            async with trio.open_nursery() as n:
                pass

        await ref.send(f"Hi from the ActorSystem")
        await ref.send(f"crash")
        await ref.send(f"Hi from the ActorSystem")

        # not possible due to type safety, comment in to see mypy in action
        # ref.send(1)
        # ref.send(True)

        # stop the system, otherwise actors will stay alive forever
        await n.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
