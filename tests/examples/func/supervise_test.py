import trio

import pyctor
from pyctor import Behavior, Behaviors
from pyctor.types import BehaviorSetup, BehaviorSignal, Context


def test_supervise():
    counter = 0

    async def handler(msg: int) -> Behavior[int]:
        nonlocal counter
        if msg == 0:
            raise ValueError("I am crashing!")
        if msg == -1:
            raise RuntimeError("Stopping!")
        counter += 1
        return Behaviors.Same

    async def exception_handler(error: Exception) -> BehaviorSignal:
        nonlocal counter
        match error:
            case ValueError():
                counter += 2
                return Behaviors.Restart
            case _:
                counter += 3
                return Behaviors.Stop

    async def main() -> None:
        with trio.fail_after(1):
            my_behavior = Behaviors.receive(handler)
            supervise_behavior = Behaviors.supervise(exception_handler, my_behavior)
            async with pyctor.open_nursery() as n:
                ref = await n.spawn(supervise_behavior)
                for i in [1, 0, 1, -1]:
                    ref.send(i)
                    # force order
                    await trio.sleep(0)

    trio.run(main)
    assert counter == 7
