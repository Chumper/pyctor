import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors

"""
Simple functional example how to change the behavior after receiving a message.
"""


async def odd_handler(msg: int) -> Behavior[int]:
    if msg % 2 == 1:
        print(f"Odd number received: {msg}")
        return Behaviors.receive_message(even_handler)
    return Behaviors.Same


async def even_handler(msg: int) -> Behavior[int]:
    if msg % 2 == 0:
        print(f"Even number received: {msg}")
        return Behaviors.receive_message(odd_handler)
    return Behaviors.Same


async def main() -> None:
    print("Actor System is starting up")
    initial_behavior = Behaviors.receive_message(odd_handler)

    async with pyctor.actor_system(initial_behavior) as asystem:
        for i in (1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4):
            await asystem.root().send(i)

        # stop the system, otherwise actors will stay alive forever
        asystem.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
