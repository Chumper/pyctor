import uuid
from typing import Optional

import cloudpickle  # type: ignore
import trio

import pyctor.behavior
import pyctor.behavior.process
import pyctor.behaviors
import pyctor.context
import pyctor.multiprocess.messages
import pyctor.multiprocess.server
import pyctor.system
import pyctor.types

# Spawning will be taken care of on other processes,
# so the only thing that will be done here is to send the spawn message to the process


class MultiProcessDispatcher(pyctor.types.Dispatcher):
    _dispatcher: pyctor.types.Dispatcher
    _nursery: trio.Nursery
    _processes: int
    _server: Optional[
        pyctor.types.Ref[pyctor.multiprocess.messages.MultiProcessMessage]
    ] = None
    _lock: trio.Lock = trio.Lock()

    def __init__(
        self, nursery: trio.Nursery, processes: int, dispatcher: pyctor.types.Dispatcher
    ) -> None:
        super().__init__()
        self._nursery = nursery
        self._processes = processes
        # we are lazy and spawn the multi process server behavior with another dispatcher
        self.dispatcher = dispatcher

    async def dispatch(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        options: pyctor.types.SpawnOptions,
    ) -> pyctor.types.Ref[pyctor.types.T]:

        # check if we need to spawn the multi process server behavior
        if not self._server:
            async with self._lock:
                name = f"multiprocess-{uuid.uuid4()}"
                self._server = await self.dispatcher.dispatch(
                    behavior=pyctor.multiprocess.server.MultiProcessServerBehavior.create(
                        max_processes=self._processes
                    ),
                    options={
                        "name": name,
                    },
                )

        # send message to multi process behavior
        behavior_bytes = cloudpickle.dumps(behavior)

        remote_ref = await self._server.ask(
            lambda x: pyctor.multiprocess.messages.SpawnCommand(
                reply_to=x, behavior=behavior_bytes, name=name
            )
        )
        return remote_ref
