import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context

"""
Simple functional example to show how to spawn a behavior with setup and teardown.
"""


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:
    # our custom setup
    print("behavior setup is running...")

    # define our message handler, this is the same as without the setup
    async def setup_handler(msg: str) -> Behavior[str]:
        print(f"setup behavior received: {msg}")
        return Behaviors.Stop

    # still on setup, log our own ref here
    print(f"My own ref is: {ctx.self().url}")

    # yield root behavior
    yield Behaviors.receive(setup_handler)

    # our custom teardown
    print("behavior teardown is running...")


async def main() -> None:
    # create our new behavior
    setup_behavior = Behaviors.setup(setup)

    # create a nursery and spawn our behavior
    async with pyctor.open_nursery() as n:
        setup_ref = await n.spawn(setup_behavior, name="setup")
        setup_ref.send(f"Hi from the outside of the behavior")


if __name__ == "__main__":
    trio.run(main)
