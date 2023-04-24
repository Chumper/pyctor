from dataclasses import dataclass
from typing import Optional

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, Ref

"""
Simple functional example how to spawn a behavior that repond to a message
"""


@dataclass
class Question:
    question: str
    reply_to: Ref[str]


@dataclass
class InvalidQuestion:
    question: str
    reply_to: Ref[str]


async def message_handler(msg: Question) -> Behavior[Question]:
    print(f"Got a new question: {msg.question}")
    msg.reply_to.send("This is the reply to your question!")
    return Behaviors.Stop


async def main() -> None:
    print("behavior tree is starting up")
    message_behavior = Behaviors.receive(message_handler)

    async with pyctor.open_nursery() as n:
        # spawn the behavior
        message_ref = await n.spawn(message_behavior, name="Answerer")

        answer = await message_ref.ask(
            lambda x: Question(question="Is this the real life?", reply_to=x)
        )
        print(f"Answer: {answer}")

    print("behavior tree was shut down")


if __name__ == "__main__":
    trio.run(main)
