import os
from multiprocessing import cpu_count
from typing import List

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref

"""
Simple functional example how to spawn a behavior on multiple cores
"""


async def message_handler(msg: str) -> Behavior[str]:
    print(f"PID {os.getpid()} got a message: {msg}")
    return Behaviors.Same


async def main() -> None:
    message_behavior = Behaviors.receive(message_handler)

    children: List[Ref[str]] = []

    async with pyctor.open_multicore_nursery() as n:
        # spawn the behaviors
        for i in range(cpu_count()):
            children.append(await n.spawn(message_behavior))

        for c in children:
            c.send(f"Hi from the behavior tree: 1")
            c.send(f"Hi from the behavior tree: 2")

        await trio.sleep(1)
        # stop the system, otherwise behaviors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
