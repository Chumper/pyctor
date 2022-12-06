
import sys
from functools import partial

import trio

from pyctor.behaviors import Behaviors
from pyctor.messages import SpawnRequest
from pyctor.types import Behavior, BehaviorSetup, Context


class MultiProcessConnectionActor:
    _parent_nursery: trio.Nursery
    _port: int

    def __init__(self, nursery: trio.Nursery, port: int) -> None:
        self._parent_nursery = nursery
        self._port = port

    async def setup(self, ctx: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:

        # spawn the process
        spawn_cmd = [
            sys.executable,
            "-m",
            "pyctor.multiprocess.child",
            "--port",
            str(self._port)
    ]
        params = partial(trio.run_process, spawn_cmd)
        process = await self._parent_nursery.start(params)

        async def setup_handler(msg: SpawnRequest) -> Behavior[SpawnRequest]:
            print("spawn")
            return Behaviors.Same

        # return a type checked behavior
        yield Behaviors.receive(setup_handler, type_check=SpawnRequest)