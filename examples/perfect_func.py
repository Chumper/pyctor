from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors


@asynccontextmanager
async def root_actor():
    # The whole lifecycle of the actor happens inside this generator function

    async def root_handler(msg: str) -> Behavior[str]:
        print(f"root actor received: {msg}")
        return Behaviors.Same

    # setup
    print("setup")
    # initial behavior
    yield Behaviors.receive(str, root_handler)
    # teardown
    print("teardown")


async def main() -> None:
    print("Actor System is starting up")

    async with pyctor.open_nursery() as n:

        # spawn actor
        # n.spawn(Behaviors.)
        root_ref = await n.spawn(root_actor)
        for i in range(10):
            root_ref.send_nowait(f"Hi from the ActorSystem {i}")

        for d in n.children():
            d.send_nowait(None)
            str_ref = d.unsafe_cast(str)
            str_ref.send_nowait("Hallo")

        await trio.sleep(1)
        await n.stop()
        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)

        # stop the system, otherwise actors will stay alive forever
    #     await asystem.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
