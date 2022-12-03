import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior

def test_send():
    counter = 0

    def counter_message_handler(i: int):
        async def message_handler(msg: int) -> Behavior[int]:
            nonlocal counter
            counter += i
            return Behaviors.Stop
        return message_handler


    async def main() -> None:
        with trio.fail_after(1):
            async with pyctor.open_nursery() as n:
                for i in [1,2,3,4,5,6,7,8,9,10]:
                    message_behavior = Behaviors.receive(counter_message_handler(i), type_check=int)
                    message_ref = await n.spawn(message_behavior)
                    message_ref.send(0)

    trio.run(main)
    assert counter == 55