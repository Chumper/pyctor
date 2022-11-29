from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor
from pyctor.behavior import Behaviors
from pyctor.types import Behavior, Ref

"""
Simple oop example to show how to spawn an actor as part of the setup behavior.
Child actors have a very simple behavior with no state.
"""


class ChildBehavior:
    async def handler(self, msg: str) -> Behavior[str]:
        print(f"child behavior received: {msg}")
        return Behaviors.Same

    def create(self) -> Behavior[str]:
        return Behaviors.receive(self.handler)


class ParentBehavior:
    _child: Ref[str]

    async def handler(self, msg: str) -> Behavior[str]:
        print(f"parent behavior received: {msg}")
        # also send to child
        self._child.send(msg)
        return Behaviors.Same

    @asynccontextmanager
    async def create(self) -> AsyncGenerator[Behavior[str], None]:
        print("Hi from parent behavior setup")
        async with pyctor.open_nursery() as n:
            self._child = await n.spawn(ChildBehavior().create(), name="parent/child")

            # yield parent behavior
            yield Behaviors.receive(self.handler)

            # child is not yet terminated here
            # self._child.send("Not yet terminated")
            # await trio.sleep(1)

            # stop the nursery, otherwise children will continue to run...
            # Be a responsible parent!
            await n.stop()

        # teardown
        print("Hi from parent behavior teardown")


async def main() -> None:
    print("Behavior Tree is starting up")

    async with pyctor.open_nursery() as n:
        parent_ref = await n.spawn(ParentBehavior().create)
        parent_ref.send(f"Hi from the Behavior Tree")

        # not possible due to type safety, comment in to see mypy in action
        # parent_ref.send(1)
        # parent_ref.send(True)

        await trio.sleep(1)

        # stop the nursery, otherwise behaviors will stay alive forever
        await n.stop()
    print("Behavior Tree was shut down")


if __name__ == "__main__":
    trio.run(main)
