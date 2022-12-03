import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


def test_children():
    counter = 0
    async def child_handler(msg: str) -> Behavior[str]:
        nonlocal counter
        counter += 2
        return Behaviors.Stop


    async def parent_setup(ctx: Context[str]) -> BehaviorSetup[str]:
        child_behavior = Behaviors.receive(child_handler)

        async with pyctor.open_nursery() as n:
            child_ref = await n.spawn(child_behavior, name="parent/child")

            async def parent_handler(msg: str) -> Behavior[str]:
                nonlocal counter
                counter += 1
                child_ref.send(msg)
                return Behaviors.Stop

            yield Behaviors.receive(parent_handler)

    async def main() -> None:
        with trio.fail_after(1):
            setup_behavior = Behaviors.setup(parent_setup)
            async with pyctor.open_nursery() as n:
                parent_ref = await n.spawn(setup_behavior, name="parent")
                parent_ref.send(f"Trigger")

    trio.run(main)
    assert counter == 3
