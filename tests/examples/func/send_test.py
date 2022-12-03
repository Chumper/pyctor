import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior

def test_send():
    counter = 0

    async def message_handler(msg: int) -> Behavior[int]:
        nonlocal counter
        counter += 1
        return Behaviors.Stop


    async def main() -> None:
        with trio.fail_after(1):
            message_behavior = Behaviors.receive(message_handler, type_check=int)
            async with pyctor.open_nursery() as n:
                message_ref = await n.spawn(message_behavior)
                message_ref.send(0)

    trio.run(main)
    assert counter == 1