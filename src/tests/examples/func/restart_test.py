import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context, SpawnOptions


def test_restart():
    counter = 0
    restart_counter = -1

    async def setup(_: Context[int]) -> BehaviorSetup[int]:
        nonlocal counter
        nonlocal restart_counter

        internal_counter = 0

        counter += 1
        restart_counter += 1

        async def setup_handler(msg: int) -> Behavior[int]:
            nonlocal internal_counter
            nonlocal counter
            nonlocal restart_counter

            internal_counter += 1
            counter += 1

            if internal_counter == 3:
                if restart_counter == 3:
                    return Behaviors.Stop

                return Behaviors.Restart

            return Behaviors.Same

        yield Behaviors.receive(setup_handler)

    async def main() -> None:
        with trio.fail_after(1):
            setup_behavior = Behaviors.setup(setup)
            async with pyctor.open_nursery() as n:
                setup_ref = await n.spawn(
                    setup_behavior, options=SpawnOptions(name="setup")
                )
                for i in range(12):
                    setup_ref.send(i)

    trio.run(main)
    assert counter == 16


if __name__ == "__main__":
    test_restart()
