#!/usr/bin/env python3

from typing import Union

import pyctor
from pyctor import ActorSystem
from pyctor.actor import Actor
from pyctor.context import Context
from pyctor.messages import PoisionPill, SystemMessage


class MyActor(Actor[str]):
    def receive(msg: Union[SystemMessage, str]):
        match msg:
            case PoisionPill():
                print(f"I am dying...")
            case _:
                print(f"Class recieved: {msg}")

def actorSpawner() -> MyActor:
    return MyActor

def handleMessage(ctx: Context, x: int):
    print(f"Callable received: {x}")

if __name__ == "__main__":
    myProp1 = pyctor.fromCallable(handleMessage)
    myProp2 = pyctor.fromProducer(actorSpawner)

    system = ActorSystem()

    ref1 = system.spawn(myProp1)
    ref2 = system.spawn(myProp2)

    system.send(ref1, 4)
    system.send(ref2, "test")
