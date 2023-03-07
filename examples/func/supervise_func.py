import trio

import pyctor
from pyctor import Behavior, Behaviors
from pyctor.types import BehaviorSetup, BehaviorSignal, Context

"""
Simple functional example how to spawn a supervised behavior that will print messages
"""


async def setup(_: Context[str]) -> BehaviorSetup[str]:
    print("Startup")
    yield Behaviors.receive(root_handler)


async def root_handler(msg: str) -> Behavior[str]:
    print(f"root actor received: {msg}")
    if msg == "crash":
        raise ValueError("I am crashing!")
    return Behaviors.Same


async def exception_handler(error: Exception) -> BehaviorSignal:
    match error:
        case ValueError():
            print(f"Restarting due to error: {error}")
            return Behaviors.Restart
        case _:
            print(f"Ignoring error: {error}")
            return Behaviors.Ignore


async def main() -> None:
    print("Actor System is starting up")
    my_behavior = Behaviors.setup(setup)
    supervise_behavior = Behaviors.supervise(exception_handler, my_behavior)

    async with pyctor.open_nursery() as n:
        ref = await n.spawn(supervise_behavior)

        ref.send(f"Hi from the ActorSystem")
        ref.send(f"crash")
        ref.send(f"Hi from the ActorSystem")

        # stop the system, otherwise actors will stay alive forever
        n.stop_all()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
