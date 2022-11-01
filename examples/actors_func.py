
import pyctor
import trio
from pyctor.behavior import Behavior, Behaviors

"""
Simple functional example how to spawn an actor that will print messages
"""

async def root_behavior(msg: str) -> Behavior[str]:
    print(f"root actor received: {msg}")
    return Behaviors.Same

async def main() -> None:
    print("Actor System is starting up")
    behavior = Behaviors.receive(root_behavior)
    
    async with pyctor.actor_system(behavior) as asystem:
        await asystem.root().send(f"Hi from the ActorSystem")
 
        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)
 
        # stop the system, otherwise actors will stay alive forever
        asystem.stop()
    print("Actor System was shut down")

if __name__ == "__main__":
    trio.run(main)
