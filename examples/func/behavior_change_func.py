import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior

"""
Simple functional example how to change the behavior after receiving a message.
"""


async def odd_handler(msg: int) -> Behavior[int]:
    if msg % 2 == 1:
        print(f"Odd number received: {msg}")
        return Behaviors.receive(even_handler)
    return Behaviors.Same


async def even_handler(msg: int) -> Behavior[int]:
    if msg % 2 == 0:
        print(f"Even number received: {msg}")
        return Behaviors.receive(odd_handler)
    return Behaviors.Same


async def main() -> None:
    print("Actor System is starting up")
    initial_behavior = Behaviors.receive(odd_handler)

    async with pyctor.open_nursery() as n:
        # spawn behavior
        ref = await n.spawn(initial_behavior)

        for i in (1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4):
            ref.send(i)
            await trio.sleep(0)  # force order

        await trio.sleep(1)

        # stop the system, otherwise actors will stay alive forever
        await n.stop()

    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
