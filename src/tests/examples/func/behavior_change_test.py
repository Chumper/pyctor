import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior


def test_behavior_change():
    counter = 0

    async def odd_handler(msg: int) -> Behavior[int]:
        if msg == 0:
            return Behaviors.Stop
        nonlocal counter
        if msg % 2 == 1:
            counter += 1
            return Behaviors.receive(even_handler)
        return Behaviors.Same

    async def even_handler(msg: int) -> Behavior[int]:
        nonlocal counter
        if msg % 2 == 0:
            counter += 2
            return Behaviors.receive(odd_handler)
        return Behaviors.Same

    async def main() -> None:
        with trio.fail_after(1):
            initial_behavior = Behaviors.receive(odd_handler)
            async with pyctor.open_nursery() as n:
                ref = await n.spawn(initial_behavior)
                for i in (1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 0):
                    ref.send(i)
                    await trio.sleep(0)  # force order

    trio.run(main)
    assert counter == 6
