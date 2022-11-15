from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors
from pyctor.types import Context, LifecycleSignal


@asynccontextmanager
async def root_actor(ctx: Context[str]) -> AsyncGenerator[Behavior[str], None]:
    async def root_handler(ctx: Context[str], msg: str) -> Behavior[str]:
        print(f"root actor received: {msg}")
        return Behaviors.Same

    # The whole lifecycle of the actor happens inside this generator function
    # setup
    print("setup")
    # start a new pyctor context
    async with pyctor.open_nursery() as n:
        # initial behavior
        yield Behaviors.receive(root_handler)
    # teardown
    print("teardown")


async def main() -> None:
    print("Actor System is starting up")

    async with pyctor.open_nursery() as n:
        # spawn actor
        # n.spawn(Behaviors.)
        for i in range(10):
            await asystem.root().send(f"Hi from the ActorSystem {i}")

        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)

        # stop the system, otherwise actors will stay alive forever
    #     await asystem.stop()
    # print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
