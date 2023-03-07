import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior

"""
Simple functional example how to spawn a behavior that will print messages
"""


async def message_handler(msg: str) -> Behavior[str]:
    print(f"message behavior received: {msg}")
    if msg == 9:
        return Behaviors.Stop
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
            # force ordering
            await trio.sleep(0)

        # not possible due to type safety, comment in to see mypy in action
        # message_ref.send(1)
        # message_ref.send(True)

        # stop the system, otherwise behaviors will stay alive forever
        n.stop_all()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
