from functools import partial
from typing import Dict

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.messages import SpawnRequest
from pyctor.multiprocess.connection import MultiProcessConnectionActor
from pyctor.types import Behavior, BehaviorSetup, Context


class MultiProcessServerActor:
    _max_processes: int
    """
    Max amount of processes
    """
    _spawn_counter: int = 0
    """
    Will be incremented each time a new behavior should be spawned.
    Indicates the process that should spawn the behavior.
    """

    _children: Dict[int, pyctor.types.Ref[SpawnRequest]] = {}
    """
    We have a child behavior for each process and ask it to spawn behaviors.
    When a child process is spawned, it will tak car of the messaging, therefore
    we only need to handle spwan requests here.
    """

    def __init__(self, max_processes: int) -> None:
        self._max_processes = max_processes

    async def connection_handler(self, stream: trio.SocketStream) -> None:
        # spawn a new behavior for this stream
        # if this is called, a new process wants to participate in spawning behaviors
        # we will spawn a new ProcessBehavior that is responsible to:
        #   * send messages to the new process
        #   * spawn new behaviors on the new process
        pass

    async def setup(self, ctx: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:

        async with pyctor.open_nursery() as n:
            # start the server
            params = partial(trio.serve_tcp, self.connection_handler, 0, host="127.0.0.1")
            n._nursery.start_soon(params)

            async def setup_handler(msg: SpawnRequest) -> Behavior[SpawnRequest]:
                # we only handle spawn requests, nothing else
                # type checking makes sure we only have that message here

                # determine the process index
                self._spawn_counter += 1 % self._max_processes

                # if the process childrend does not exist yet, we start it
                if self._spawn_counter not in self._children:
                    setup_behavior = Behaviors.setup(MultiProcessConnectionActor(nursery=n._nursery).setup)
                    self._children[self._spawn_counter] = await n.spawn(setup_behavior)

                # send same spawn message to child process
                self._children[self._spawn_counter].send(msg=msg)

                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=SpawnRequest)

            # cancel this scope
            n._nursery.cancel_scope.cancel()
