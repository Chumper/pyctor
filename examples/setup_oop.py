
import trio

import pyctor
from pyctor.behavior import Behavior, Behaviors, Context
from pyctor.types import Actor, Ref

"""
Simple oop example to show how to spawn an actor as part of the setup behavior.
Child actors have a very simple behavior with no state.
"""

class ChildActor(Actor[str]):
    async def on_message(self, msg: str) -> Behavior[str]:
        print(f"child actor received: {msg}")
        return Behaviors.Same

    def create(self) -> Behavior[str]:
        return Behaviors.receive_message(self.on_message)


class ParentActor(Actor[str]):
    _child: Ref[str]

    async def on_message(self, msg: str) -> Behavior[str]:
        print(f"root actor received: {msg}")
        # also send to child_ref
        await self._child.send(msg)
        return Behaviors.Same

    async def setup(self, ctx: Context[str]) -> Behavior[str]:
        print("Hi from root actor setup")
        
        # spawn child actors
        self._child = await ctx.spawn(ChildActor().create())

        # return root behavior
        return Behaviors.receive_message(self.on_message)

    def create(self) -> Behavior[str]:
        return Behaviors.setup(self.setup)


async def main() -> None:
    print("Actor System is starting up")
    
    async with pyctor.actor_system(ParentActor().create()) as asystem:
        await asystem.root().send(f"Hi from the ActorSystem")
 
        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)
 
        # stop the system, otherwise actors will stay alive forever
        await asystem.stop()
    print("Actor System was shut down")

if __name__ == "__main__":
    trio.run(main)
