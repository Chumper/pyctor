from typing import Awaitable
import tractor
import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors, LifecycleSignal

# define root behavior
async def root_receive(msg: str) -> Behavior[str]:
    print(f"root actor received: {msg}")
    return Behaviors.Same

async def main() -> None:
    print("Starting")
    behavior = Behaviors.receive(root_receive)
    
    async with pyctor.actor_system(behavior) as asystem:
        for i in range(10):
            await asystem.root().send(f"Hi from the ActorSystem: {i}")
  
        # asystem.root().send(1)
        # asystem.root().send(LifecycleSignal.Started)
        # await trio.sleep(1)
        asystem.stop()

async def my_print() -> None:
    print("Async Print")

if __name__ == "__main__":
    trio.run(main)