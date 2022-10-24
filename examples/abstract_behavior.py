#!/usr/bin/env python3



from logging import root

from pyctor.behavior import AbstractBehavior, Behavior, Receive
from pyctor.context import Context


class Protocol:
    pass


class Request1(Protocol):
    pass


class Request2(Protocol):
    pass


class MyBehavior(AbstractBehavior[Protocol]):
    def handleRequest1(self, init: Request1) -> Behavior[Protocol]:
        pass
    def handleRequest2(self, init: Request2) -> Behavior[Protocol]:
        pass

    def createReceive(self) -> Receive[Protocol]:
        return self.newReceiveBuilder() \
            .onMessage(Request1, self.handleRequest1) \
            .onMessage(Request2, self.handleRequest2) \
            .build()



def main() -> None:
    
    rootRef = Context.fromRootBehavior(MyBehavior())
    rootRef.send(Request1())
    rootRef.stop() # stopping the root will stop the system


if __name__ == "__main__":
    main()
