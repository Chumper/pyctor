import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context

"""
Simple functional example to show how to spawn a behavior with setup and teardown.
Child behaviors have a very simple behavior with no state.
"""


async def child_handler(msg: str) -> Behavior[str]:
    print(f"child behavior received: {msg}")
    return Behaviors.Same


async def parent_setup(ctx: Context[str]) -> BehaviorSetup[str]:
    # spawn child behaviors
    child_behavior = Behaviors.receive(child_handler)

    async with pyctor.open_nursery() as n:
        child_ref = await n.spawn(child_behavior, options={"name": "parent/child"})

        async def parent_handler(msg: str) -> Behavior[str]:
            print(f"parent behavior received: {msg}")
            # also send to child_ref
            child_ref.send(msg)
            return Behaviors.Same

        # yield root behavior
        yield Behaviors.receive(parent_handler)

        # stop the nursery, otherwise children will continue to run...
        # Be a responsible parent!
        n.stop_all()


async def main() -> None:
    setup_behavior = Behaviors.setup(parent_setup)
    async with pyctor.open_nursery() as n:
        parent_ref = await n.spawn(setup_behavior, options={"name": "parent"})

        parent_ref.send(f"Hi from the behavior system")

        await trio.sleep(1)
        # stop the system, otherwise behaviors will stay alive forever
        n.stop_all()


if __name__ == "__main__":
    trio.run(main)
