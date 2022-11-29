from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor
from pyctor.behavior import Behaviors
from pyctor.types import Behavior

"""
Simple functional example to show how to spawn a behavior with setup and teardown.
Child behaviors have a very simple behavior with no state.
"""


async def child_handler(msg: str) -> Behavior[str]:
    print(f"child behavior received: {msg}")
    return Behaviors.Same


# If a setup and/or teardown method is required, then an AsyncGenerator needs to be provided.
# For that the annotation @asynccontextmanager is useful to not implement the whole interface.
# The behavior is then yielded. The system now handles setup and teardown correctly.
@asynccontextmanager
async def parent_setup() -> AsyncGenerator[Behavior[str], None]:
    # setup
    print("Hi from parent behavior setup")

    # spawn child behaviors
    child_behavior = Behaviors.receive(child_handler)

    async with pyctor.open_nursery() as n:
        child_ref = await n.spawn(child_behavior, name="parent/child")

        async def parent_handler(msg: str) -> Behavior[str]:
            print(f"parent behavior received: {msg}")
            # also send to child_ref
            child_ref.send(msg)
            return Behaviors.Same

        # yield root behavior
        yield Behaviors.receive(parent_handler)

        # child is not yet terminated here
        # child_ref.send("Not yet terminated")
        # await trio.sleep(1)

        # stop the nursery, otherwise children will continue to run...
        # Be a responsible parent!
        await n.stop()

    # child is already terminated here
    # await child_ref.send("Will error out")

    # teardown
    print("Hi from parent behavior teardown")


async def main() -> None:
    print("behavior tree is starting up")

    async with pyctor.open_nursery() as n:
        parent_ref = await n.spawn(parent_setup, name="parent")

        parent_ref.send(f"Hi from the ActorSystem")

        await trio.sleep(1)
        # stop the system, otherwise actors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
