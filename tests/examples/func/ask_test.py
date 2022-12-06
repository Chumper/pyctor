from dataclasses import dataclass
from typing import Optional

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref


def test_ask():
    counter = 0

    @dataclass
    class Increase:
        amount: int
        reply_to: Ref[int]

    async def message_handler(msg: Increase) -> Behavior[Increase]:
        msg.reply_to.send(msg.amount)
        if msg.amount == 4:
            return Behaviors.Stop
        return Behaviors.Same

    async def main() -> None:
        nonlocal counter
        message_behavior = Behaviors.receive(message_handler)

        with trio.fail_after(1):
            async with pyctor.open_nursery() as n:
                message_ref = await n.spawn(message_behavior)
                for i in range(5):
                    answer = await message_ref.ask(lambda x: Increase(amount=i, reply_to=x))
                    counter += answer

    trio.run(main)
    assert counter == 10
