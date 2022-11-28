from multiprocessing import Process, Queue, current_process
from typing import Awaitable, Callable

import trio


def trio_main(func: Callable[[], Awaitable[None]]):
    trio.run(func)


def worker_main(q: Queue) -> None:
    trio_main(worker)


async def worker() -> None:
    proc_name = current_process().name
    print(f"Doing something fancy in {proc_name}")


async def main() -> None:
    async with trio.open_nursery() as n:
        p = Process(target=worker_main, args=(queue,))
        p.start()


if __name__ == "__main__":
    trio_main(main)
