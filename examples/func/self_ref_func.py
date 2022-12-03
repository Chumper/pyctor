import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref

"""
Simple functional example how to send message to its own ref
"""


async def message_handler(msg: str) -> Behavior[str]:

    print(f"I am saying: {msg}")
    return Behaviors.Same


# def self_handler(ref: Ref[str]):
#     print("I got my ref!")
#     async def message_handler(msg: str) -> Behavior[str]:
#         if msg.startswith("remember:"):
#             # send message to self
#             print(f"I try to remember: {msg}")
#             ref.send(f"I remember: {msg}")
#             return Behaviors.Same

#         print(f"I am saying: {msg}")
#         return Behaviors.Same
#     return Behaviors.receive(message_handler)


async def main() -> None:
    print("behavior tree is starting up")
    ref_behavior = Behaviors.with_self(self_handler)

    async with pyctor.open_nursery() as n:
        # spawn the behavior
        message_ref = await n.spawn(ref_behavior)

        message_ref.send(f"It is pretty cold outside")
        message_ref.send(f"I will go outside")
        message_ref.send(f"think: Don't forget your coat")

        await trio.sleep(1)
        # stop the system, otherwise behaviors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
