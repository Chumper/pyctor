#!/usr/bin/env python3


from abc import ABC
from pyctor.actor import Actor
from pyctor.behavior import AbstractBehavior, Behavior, Receive
from pyctor.messages import Message, PoisionPill, Started


class Protocol:
    pass


class Request1(Protocol):
    pass


class Request2(Protocol):
    pass


class MyBehavior(AbstractBehavior[Protocol]):
    def handleRequest1(self, init: Request1) -> Behavior[Protocol]:
        pass

    def createReceive(self) -> Receive[Protocol]:
        return self.newReceiveBuilder().onMessage(Request1, self.handleRequest1).build()



def main() -> None:
    pass


if __name__ == "__main__":
    main()
