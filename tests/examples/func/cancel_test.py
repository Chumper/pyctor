import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


def test_cancel():
    counter = 0

    async def child_handler(msg: str) -> Behavior[str]:
        return Behaviors.Same

    async def parent_setup(ctx: Context[str]) -> BehaviorSetup[str]:
        nonlocal counter

        child_behavior = Behaviors.receive(child_handler)
        counter += 1

        async with pyctor.open_nursery() as n:
            child_ref = await n.spawn(child_behavior, name="parent/child")

            async def parent_handler(msg: str) -> Behavior[str]:
                child_ref.send(msg)
                return Behaviors.Same

            yield Behaviors.receive(parent_handler)
            
            # you need to stop children explicitly!
            # If you are not doing that they will continue to run and this nursery will never close!
            child_ref.stop()

            # either stop explicitly or call stop on the nursery
            # await n.stop()

        counter += 1

    async def main() -> None:
        with trio.fail_after(20):
            setup_behavior = Behaviors.setup(parent_setup)
            async with pyctor.open_nursery() as n:
                parent_ref = await n.spawn(setup_behavior, name="parent")
                parent_ref.send(f"Trigger")
                await trio.sleep(0)
                # terminate the system
                n.stop_all()

    trio.run(main)
    assert counter == 2

if __name__ == "__main__":
    test_cancel()