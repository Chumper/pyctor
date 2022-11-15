import os
from multiprocessing import cpu_count

import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors
from pyctor.types import Context

"""
Simple functional example how to spawn actors on multiple cores
"""


async def process_setup(ctx: Context[str]) -> Behavior[str]:
    print(f"Yo, i'm '{ctx.self().address()}' " f"running in pid {os.getpid()}")

    async def process_handle(msg: str) -> Behavior[str]:
        return Behaviors.Same

    # return root behavior
    return Behaviors.receive_message(process_handle)


async def main() -> None:
    print("Actor System is starting up")
    process_behavior = Behaviors.setup(process_setup)

    async with pyctor.open_nursery() as n:
        with pyctor.multicore_dispatcher(n):
            for i in range(cpu_count()):
                print(f"spawning worker_{i}")
                ref = await n.spawn(process_behavior, name=f"worker_{i}")
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
