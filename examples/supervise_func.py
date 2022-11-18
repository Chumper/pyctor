import trio

import pyctor
from pyctor import Behavior, Behaviors, SuperviseStrategy

"""
Simple functional example how to spawn an actor that will print messages
"""


async def root_handler(msg: str) -> Behavior[str]:
    print(f"root actor received: {msg}")
    if msg == "crash":
        raise ValueError("I am crashing!")
    return Behaviors.Same


async def exception_handler(error: Exception) -> SuperviseStrategy:
    match error:
        case ValueError():
            return SuperviseStrategy.Restart
        case _:
            return SuperviseStrategy.Ignore


async def main() -> None:
    print("Actor System is starting up")
    root_behavior = Behaviors.receive(root_handler)
    supervise_behavior = Behaviors.supervise(exception_handler, root_behavior)

    async with pyctor.open_nursery() as n:
        ref = await n.spawn(supervise_behavior)

        await ref.send(f"Hi from the ActorSystem")
        await ref.send(f"crash")
        await ref.send(f"Hi from the ActorSystem")

        # not possible due to type safety, comment in to see mypy in action
        # ref.send(1)
        # ref.send(True)

        # stop the system, otherwise actors will stay alive forever
        await n.stop()
    print("Actor System was shut down")


if __name__ == "__main__":
    trio.run(main)
