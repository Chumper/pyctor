import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior

"""
Simple object orientated example how to spawn an actor that will print messages it receives
"""


class MessageBehavior:
    async def message_handler(self, msg: str) -> Behavior[str]:
        print(f"message behavior received: {msg}")
        return Behaviors.Same

    def create(self) -> Behavior[str]:
        return Behaviors.receive(self.message_handler)


async def main() -> None:
    print("behavior tree is starting up")
    async with pyctor.open_nursery() as n:
        # spawn the actor
        message_ref = await n.spawn(MessageBehavior().create())

        for i in range(10):
            # message order is not guaranteed!
            message_ref.send(f"Hi from the Behavior Tree {i}")

        # not possible due to type safety, comment in to see mypy in action
        # message_ref.send(1)
        # message_ref.send(True)

        await trio.sleep(1)
        # stop the system, otherwise actors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
