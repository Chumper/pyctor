import threading
from multiprocessing import cpu_count
from uuid import uuid4

import trio

import cloudpickle # type: ignore

import pyctor.behavior
import pyctor.behavior.process
import pyctor.behaviors
import pyctor.context
import pyctor.multiprocess.server
import pyctor.multiprocess.messages
import pyctor.system
import pyctor.types
from pyctor.registry import RegistryImpl

# Plan:
# determine next process
# check if process is already started
# start process if needed
# send spawn request to process
#


class MultiProcessState:
    _ref: pyctor.types.Ref[pyctor.multiprocess.messages.MultiProcessMessage] | None = None
    """
    The actual ref of the behavior that spawns the behaviors on another process
    """
    _lock = trio.Lock()
    """
    A lock to initially spawn the multi process behavior 
    """

    async def ref(self) -> pyctor.types.Ref[pyctor.multiprocess.messages.MultiProcessMessage]:
        async with self._lock:
            if not self._ref:
                # define channels
                send: trio.abc.SendChannel
                receive: trio.abc.ReceiveChannel
                registry: pyctor.types.Registry = pyctor.system.registry.get()

                # create a new memory channel
                send, receive = trio.open_memory_channel(0)
                # register and get ref
                self._ref = await registry.register(channel=send, name=str(uuid4()))

                # server behavior
                server_behavior = pyctor.multiprocess.server.MultiProcessServerActor.create(max_processes=2)

                # create the process
                b = pyctor.behavior.process.BehaviorProcessorImpl[pyctor.types.T](
                    behavior=server_behavior, channel=receive, context=pyctor.context.ContextImpl(self._ref)
                )

                # start in the nursery
                # self._nursery.start_soon(b.behavior_task)
                trio.lowlevel.spawn_system_task(b.behavior_task)

        return self._ref


state: trio.lowlevel.RunVar = trio.lowlevel.RunVar("state", MultiProcessState())
"""
trio.run local state to determine the next process.
"""

# Spawning will be taken care of on other processes,
# so the only thing that will be done here is to send the spawn message to the process


class MultiProcessDispatcher(pyctor.types.Dispatcher):
    _nursery: trio.Nursery
    _processes: int
    _state: MultiProcessState

    def __init__(self, nursery: trio.Nursery, processes: int) -> None:
        super().__init__()
        self._nursery = nursery
        self._processes = processes
        self._state = state.get()

    async def dispatch(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        name: str,
    ) -> pyctor.types.Ref[pyctor.types.T]:
        # send message to multi process behavior
        ref = await self._state.ref()
        # use cloudpickle to pickle the behavior
        behavior_bytes = cloudpickle.dumps(behavior)
        
        remote_ref = await ref.ask(lambda x: pyctor.multiprocess.messages.SpawnCommand(reply_to=x, behavior=behavior_bytes, name=name))
        return remote_ref
