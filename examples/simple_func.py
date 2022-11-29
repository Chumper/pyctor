import trio

import pyctor
from pyctor.behavior import Behaviors
from pyctor.types import Behavior

"""
Simple functional example how to spawn a behavior that will print messages
"""


async def message_handler(msg: str) -> Behavior[str]:
    print(f"message behavior received: {msg}")
    return Behaviors.Same


async def main() -> None:
    print("behavior tree is starting up")
    message_behavior = Behaviors.receive(message_handler)

    async with pyctor.open_nursery() as n:
        # spawn the behavior
        message_ref = await n.spawn(message_behavior)

        for i in range(10):
            # message order is not guaranteed!
            message_ref.send(f"Hi from the Behavior Tree {i}")

        # not possible due to type safety, comment in to see mypy in action
        # await message_ref.send(1)
        # await message_ref.send(True)

        await trio.sleep(1)
        # stop the system, otherwise behaviors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
