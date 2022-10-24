#!/usr/bin/env python3


from typing import List
import pyctor
from pyctor.actor import Actor
from pyctor.behavior import AbstractBehavior, Behavior, Receive
from pyctor.behaviors import Behaviors
from pyctor.context import Context
from pyctor.messages import Message, PoisionPill, Started


class MyActor(AbstractBehavior[str]):
    def createReceive(self) -> Receive[str]:
        def onString(msg: Message[str]) -> Behavior[str]:
            match msg:
                case Started():
                    print(f"I was started...")
                case PoisionPill():
                    print(f"I am dying...")
                case _:
                    print(f"Class recieved: {msg}")
            return self

        return self.newReceiveBuilder().onMessage(str, onString).build()


def handleMessage(ctx: Context, x: Message[int]) -> None:
    print(f"Callable received: {x}")


def main() -> None:
    myProp1 = Behaviors.fromCallable(handleMessage)
    myProp2 = Behaviors.fromBehavior(MyActor)

    system = pyctor.newRootContext()

    ref1 = system.spawn(myProp1)
    ref2 = system.spawn(myProp2)

    system.send(ref1, 4)
    system.send(ref1, "test")  # should fail
    system.send(ref2, "test")
    system.send(ref2, 4)  # should fail


if __name__ == "__main__":
    main()
