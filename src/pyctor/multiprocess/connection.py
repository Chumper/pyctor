import sys
from functools import partial

import trio

from pyctor.behaviors import Behaviors
from pyctor.messages import SpawnRequest
from pyctor.types import Behavior, BehaviorSetup, Context


class MultiProcessConnectionActor:
    _stream: trio.SocketStream

    def __init__(self, stream: trio.SocketStream) -> None:
        self._stream = stream

    async def setup(self, ctx: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:
        async def setup_handler(msg: SpawnRequest) -> Behavior[SpawnRequest]:
            print("spawn")
            return Behaviors.Same

        # return a type checked behavior
        yield Behaviors.receive(setup_handler, type_check=SpawnRequest)
