import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context, SpawnOptions


def test_setup():
    counter = 0

    async def setup(_: Context[str]) -> BehaviorSetup[str]:
        nonlocal counter

        counter += 1

        async def setup_handler(msg: str) -> Behavior[str]:
            return Behaviors.Stop

        yield Behaviors.receive(setup_handler)

        counter += 2

    async def main() -> None:
        with trio.fail_after(1):
            setup_behavior = Behaviors.setup(setup)
            async with pyctor.open_nursery() as n:
                setup_ref = await n.spawn(
                    setup_behavior, options=SpawnOptions(name="setup")
                )
                setup_ref.send(f"Stop")

    trio.run(main)
    assert counter == 3
