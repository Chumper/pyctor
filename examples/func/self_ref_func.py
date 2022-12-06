import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:
    async def setup_handler(msg: str) -> Behavior[str]:
        print(f"{ctx.self().url} received: {msg}")
        # also send to child_ref
        return Behaviors.Stop

    # yield root behavior
    yield Behaviors.receive(setup_handler)


async def main() -> None:
    setup_behavior = Behaviors.setup(setup)
    async with pyctor.open_nursery() as n:
        for i in range(3):
            setup_ref = await n.spawn(setup_behavior)
            setup_ref.send(f"Hi from the outside the behavior")


if __name__ == "__main__":
    trio.run(main)
