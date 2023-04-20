import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:

    async with (
        ctx.with_stash(100) as stash,
        ctx.with_timer() as timer,
        ctx.with_self() as ref,
    ):

        async def parent_handler(msg: str) -> Behavior[str]:
            print(f"parent behavior received: {msg}")
            # also send to child_ref
            return Behaviors.Same

        yield Behaviors.receive(parent_handler)


async def main() -> None:
    print("behavior tree is starting up")

    setup_behavior = Behaviors.setup(setup)
    async with pyctor.open_nursery() as n:
        parent_ref = await n.spawn(setup_behavior, name="parent")

        parent_ref.send(f"Hi from the Behavior system")

        await trio.sleep(1)
        # stop the system, otherwise behaviors will stay alive forever
        await n.stop()
    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
