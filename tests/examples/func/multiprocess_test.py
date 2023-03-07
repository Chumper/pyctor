import logging
import os
from dataclasses import dataclass
from typing import Set

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref


logging.basicConfig(level="DEBUG")

@dataclass
class PIDRequest:
    reply_to: Ref[int]


def test_multiprocess():
    num_processes = 2
    pids: Set[int] = ()

    async def message_handler(msg: PIDRequest) -> Behavior[PIDRequest]:
        print(f"responding with: {os.getpid()}")
        msg.reply_to.send(os.getpid())
        return Behaviors.Stop

    async def main() -> None:
        # with trio.fail_after(1):
        message_behavior = Behaviors.receive(message_handler, type_check=PIDRequest)

        print(f"main: {os.getpid()}")

        async with pyctor.open_multiprocess_nursery() as n:
            for i in range(num_processes):
                ref = await n.spawn(message_behavior)
                pid = await ref.ask(lambda x: PIDRequest(reply_to=x))
                assert pid not in pids
                pids.add(pid)
        
        async with pyctor.open_nursery() as n:
            ref = await n.spawn(message_behavior)
            pid = await ref.ask(lambda x: PIDRequest(reply_to=x))
            assert pid not in pids
            pids.add(pid)

    trio.run(main)
    assert len(pids) == num_processes + 1


if __name__ == "__main__":
    test_multiprocess()
