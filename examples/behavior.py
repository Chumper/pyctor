#!/usr/bin/env python3


from abc import ABC
from weakref import ProxyType
from pyctor.actor import Actor
from pyctor.behavior import AbstractBehavior, Behavior, Receive
from pyctor.behaviors import Behaviors
from pyctor.context import Context
from pyctor.messages import Message, PoisionPill, Started


class Protocol:
    pass


class Request1(Protocol):
    pass


class Request2(Protocol):
    pass

def setup(ctx: Context[Protocol]) -> Behavior[Protocol]:
    # childRef = ctx.spawn()
    pass


def main() -> None:
    Behaviors.setup(setup)


if __name__ == "__main__":
    main()
