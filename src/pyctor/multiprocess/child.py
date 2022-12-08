import argparse

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context


def get_port() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Port for the multi processing", required=True)
    return int(parser.parse_args().port)


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:

    stream = await trio.open_tcp_stream("127.0.0.1", get_port())

    print(f"connected to port {get_port()}")

    await stream.send_all(b"test")

    async def setup_handler(msg: str) -> Behavior[str]:
        return Behaviors.Same

    yield Behaviors.receive(setup_handler)


async def main() -> None:

    setup_behavior = Behaviors.setup(setup)
    async with pyctor.open_nursery() as n:
        await n.spawn(setup_behavior)


if __name__ == "__main__":
    trio.run(main)
