import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


def test_watch():
    counter = 0
    async def message_handler(msg: int) -> Behavior[int]:
        nonlocal counter
        counter += 1

        if msg == 9:
            return Behaviors.Stop
        return Behaviors.Same

    async def setup(ctx: Context[str]) -> BehaviorSetup[str]:
        async with pyctor.open_nursery() as n:
            # spawn watched behavior
            child_ref = await n.spawn(Behaviors.receive(message_handler))

            await ctx.watch(child_ref, "TERMINATED!!!!")

            async def setup_handler(msg: str) -> Behavior[str]:
                if msg == "TERMINATED!!!!":
                   nonlocal counter
                   counter += 1
                   return Behaviors.Stop
                if msg == "Do Work!!!":
                    for i in range(10):
                        child_ref.send(i)
                        # force order
                        await trio.sleep(0)
                return Behaviors.Same

            yield Behaviors.receive(setup_handler)

    async def main() -> None:
        with trio.fail_after(1):
            setup_behavior = Behaviors.setup(setup)
            async with pyctor.open_nursery() as n:
                setup_ref = await n.spawn(setup_behavior)
                setup_ref.send(f"Do Work!!!")

    trio.run(main)
    assert counter == 11

if __name__ == "__main__":
    test_watch()