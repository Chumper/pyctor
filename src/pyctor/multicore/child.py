import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorSetup, Context

import argparse


def get_port() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", help="Port for the multi processing", required=True
    )
    return parser.parse_args().port


async def setup(ctx: Context[str]) -> BehaviorSetup[str]:
    
    stream = await trio.open_tcp_stream("127.0.0.1", get_port())

    async def setup_handler(msg: str) -> Behavior[str]:
        return Behaviors.Stop

    yield Behaviors.receive(setup_handler)

async def main() -> None:
    
    with trio.fail_after(1):
        setup_behavior = Behaviors.setup(setup)
        async with pyctor.open_nursery() as n:
            setup_ref = await n.spawn(setup_behavior, name="setup")
            setup_ref.send(f"Stop")

if __name__ == "__main__":
    trio.run(main)