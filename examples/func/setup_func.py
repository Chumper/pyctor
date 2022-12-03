import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context

"""
Simple functional example to show how to spawn a behavior with setup and teardown.
"""


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:
    # setup
    print("behavior setup is running...")

    async def setup_handler(msg: str) -> Behavior[str]:
        print(f"setup behavior received: {msg}")
        # also send to child_ref
        return Behaviors.Stop

    # yield root behavior
    yield Behaviors.receive(setup_handler)

    # teardown
    print("behavior teardown is running...")


async def main() -> None:
    setup_behavior = Behaviors.setup(setup)

    async with pyctor.open_nursery() as n:
        setup_ref = await n.spawn(setup_behavior, name="setup")
        setup_ref.send(f"Hi from the outside the behavior")


if __name__ == "__main__":
    trio.run(main)
