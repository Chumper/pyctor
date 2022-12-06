from typing import Never
import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.messages import MultiProcessBase, SpawnRequest
from pyctor.types import Behavior, BehaviorSetup, Context


class MultiProcessServerActor():
    _children: pyctor.types.Ref[SpawnRequest]
    """
    We have a child behavior for each core and ask it to spawn behaviors
    """
    
    async def connection_handler(self, stream: trio.SocketStream) -> None:
        # spawn a new behavior for this stream
        # if this is called, a new core wants to participate in spawning behaviors
        # we will spawn a new CoreBehavior that is responsible to:
        #   * send messages to the new process
        #   * spawn new behaviors on the new process
        pass

    async def setup(self, ctx: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:

        async with pyctor.open_nursery() as n:
            # start the server
            n._nursery.start_soon(trio.serve_tcp, self.connection_handler, 0, "127.0.0.1")

            async def setup_handler(msg: SpawnRequest) -> Behavior[SpawnRequest]:
                # we only handle spawn requests, nothing else
                # type checking makes sure we only have that message here

                # determine the child index
                msg.core % 

                return Behaviors.Stop

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=SpawnRequest)
            
            # cancel this scope
            n._nursery.cancel_scope.cancel()