import trio

import pyctor
from pyctor.behavior import Actor, Behavior, Behaviors

"""
Simple object orientated example how to spawn an actor that will print messages it receives
"""


class RootActor(Actor[str]):
    async def root_handler(self, msg: str) -> Behavior[str]:
        print(f"root actor received: {msg}")
        return Behaviors.Same

    def create(self) -> Behavior[str]:
        return Behaviors.receive_message(self.root_handler)


async def main() -> None:
    print("Actor System is starting up")
    async with pyctor.actor_system(RootActor().create()) as asystem:
        for i in range(10):
            await asystem.root().send(f"Hi from the ActorSystem {i}")

        # not possible due to type safety, comment in to see mypy in action
        # asystem.root().send(1)
        # asystem.root().send(True)

        # stop the system, otherwise actors will stay alive forever
        await asystem.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
