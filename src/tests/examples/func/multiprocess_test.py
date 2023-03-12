import logging
import os
from typing import List, Set

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref
from tests.examples.func.messages import PIDRequest

logging.basicConfig(level="DEBUG")


def test_multiprocess():
    num_processes = 2
    pids: Set[int] = set()

    async def message_handler(msg: PIDRequest) -> Behavior[PIDRequest]:
        print(f"responding with: {os.getpid()}")
        msg.reply_to.send(os.getpid())
        return Behaviors.Stop

    async def main() -> None:
        # with trio.fail_after(1):
        message_behavior = Behaviors.receive(message_handler, type_check=PIDRequest)

        print(f"main: {os.getpid()}")

        async with pyctor.open_multiprocess_nursery(processes=num_processes) as n:
            refs: List[Ref[PIDRequest]] = []
            # spawn processes
            for i in range(num_processes):
                ref = await n.spawn(message_behavior, name=f"user/worker-{i}")
                refs.append(ref)
            # all spawned, get pid
            for ref in refs:
                pid = await ref.ask(lambda x: PIDRequest(reply_to=x))
                assert pid not in pids
                pids.add(pid)
            n.stop_all()

        async with pyctor.open_nursery() as n:
            ref = await n.spawn(message_behavior)
            pid = await ref.ask(lambda x: PIDRequest(reply_to=x))
            assert pid not in pids
            pids.add(pid)

    # trio.run(main)
    # assert len(pids) == num_processes + 1


if __name__ == "__main__":
    test_multiprocess()
