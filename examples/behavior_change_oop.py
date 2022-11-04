import trio

import pyctor
from pyctor.behavior import Actor, Behavior, Behaviors

"""
Simple object orientated example how to change the behavior after receiving a message.
"""


class BehaviorActor(Actor[int]):
    async def odd_handler(self, msg: int) -> Behavior[int]:
        if msg % 2 == 1:
            print(f"Odd number received: {msg}")
            return Behaviors.receive_message(self.even_handler)
        return Behaviors.Same

    async def even_handler(self, msg: int) -> Behavior[int]:
        if msg % 2 == 0:
            print(f"Even number received: {msg}")
            return Behaviors.receive_message(self.odd_handler)
        return Behaviors.Same

    def create(self) -> Behavior[int]:
        return Behaviors.receive_message(self.odd_handler)

    pass


async def main() -> None:
    print("Actor System is starting up")

    async with pyctor.actor_system(BehaviorActor().create()) as asystem:
        for i in (1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4):
            await asystem.root().send(i)

        # stop the system, otherwise actors will stay alive forever
        await asystem.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
