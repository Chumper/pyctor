import sys
import threading
from functools import partial
from typing import Dict, List

import trio

import pyctor
from pyctor.behaviors import Behaviors
from pyctor.multiprocess.connection import MultiProcessServerConnectionActor
from pyctor.multiprocess.messages import MultiProcessBase, SpawnRequest
from pyctor.types import Behavior, BehaviorNursery, BehaviorSetup, Context


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
    _processes: Dict[int, trio.Process] = {}
    _nursery: BehaviorNursery | None = None
    _processes_connected: Dict[int, trio.Event] = {}
    _children: Dict[int, pyctor.types.Ref[MultiProcessBase]] = {}

    def __init__(self, max_processes: int) -> None:
        self._max_processes = max_processes

    async def connection_handler(self, stream: trio.SocketStream) -> None:
        # spawn a new behavior for this stream
        # if this is called, a new process wants to participate in spawning behaviors
        # we will spawn a new ProcessBehavior that is responsible to:
        #   * send messages to the new process
        #   * spawn new behaviors on the new process
        print("connected, I think...")
        if self._nursery:
            stream_behavior = Behaviors.setup(
                MultiProcessServerConnectionActor(stream=stream).setup
            )
            stream_ref = await self._nursery.spawn(stream_behavior)
            self._children[self._spawn_counter] = stream_ref
            self._processes_connected[self._spawn_counter].set()

    async def start_process(self, index: int, port: int) -> None:
        self._processes_connected[index] = trio.Event()

        # spawn the process
        spawn_cmd = [
            sys.executable,
            "-m",
            "pyctor.multiprocess.child",
            "--port",
            str(port),
        ]
        process: trio.Process
        params = partial(trio.run_process, spawn_cmd)
        if self._nursery:
            process = await self._nursery._nursery.start(params)

            # wait until the process has connected back and there is a ref
            self._processes[index] = process
            await self._processes_connected[index].wait()

    async def setup(self, _: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:

        async with pyctor.open_nursery() as n:
            self._nursery = n

            # start the server
            params = partial(
                trio.serve_tcp, self.connection_handler, 0, host="127.0.0.1"
            )
            listeners: List[trio.SocketListener] = await n._nursery.start(params)
            
            # get the port
            port = listeners[0].socket.getsockname()[1]

            async def setup_handler(msg: SpawnRequest) -> Behavior[SpawnRequest]:
                # we only handle spawn requests, nothing else
                # type checking makes sure we only have that message here

                # determine the process index
                self._spawn_counter += 1 % self._max_processes

                # if the process childrend does not exist yet, we start it
                # with trio.fail_after(2):
                if self._spawn_counter not in self._processes:
                    await self.start_process(index=self._spawn_counter, port=port)

                # send same spawn message to child process
                self._children[self._spawn_counter].send(msg=msg)

                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=SpawnRequest)

            # cancel this scope
            n._nursery.cancel_scope.cancel()
