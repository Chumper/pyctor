
import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors, Context, LoggingBehaviorHandlerImpl

"""
Simple functional example to show how to spawn an actor as part of the setup behavior.
Child actors have a very simple behavior with no state.
"""

async def child_handle(msg: str) -> Behavior[str]:
    print(f"child actor received: {msg}")
    return Behaviors.Same


async def root_setup(ctx: Context[str]) -> Behavior[str]:
    print("Hi from root actor setup")
    
    # spawn child actors
    child_behavior = Behaviors.receive_message(child_handle)
    child_ref = await ctx.spawn(child_behavior)

    async def root_handle(msg: str) -> Behavior[str]:
        print(f"root actor received: {msg}")
        # also send to child_ref
        child_ref.send(msg)
        return Behaviors.Same

    # return root behavior
    return Behaviors.receive_message(root_handle)

async def main() -> None:
    print("Actor System is starting up")
    behavior = Behaviors.setup(root_setup)
    
    async with pyctor.root_behavior(LoggingBehaviorHandlerImpl(behavior)) as asystem:
        asystem.root().send(f"Hi from the ActorSystem")
 
        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)
 
        # stop the system, otherwise actors will stay alive forever
        asystem.stop()
    print("Actor System was shut down")

if __name__ == "__main__":
    trio.run(main)
