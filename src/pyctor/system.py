import contextvars
import multiprocessing
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.dispatch.multi_process
import pyctor.dispatch.single_process
import pyctor.spawn
import pyctor.types
import pyctor.registry

is_child: bool = True
"""
trio.run flag to indicate if the current process is a child or the server
"""
registry: trio.lowlevel.RunVar = trio.lowlevel.RunVar(name="registry", default=pyctor.registry.RegistryImpl()) # type: ignore
"""
trio.run local registry for all behaviors. Effectively one core.
"""
nursery = contextvars.ContextVar[pyctor.types.BehaviorNursery]("nursery")
"""
Context var for each nursery. Is used by the refs to schedule a send in the current nursery
"""


class BehaviorNurseryImpl(pyctor.spawn.SpawnerImpl, pyctor.types.BehaviorNursery):
    def __init__(self, nursery: trio.Nursery, dispatcher: pyctor.types.Dispatcher) -> None:
        super().__init__(
            nursery=nursery,
            dispatcher=dispatcher,
        )


@asynccontextmanager
async def open_nursery() -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            behavior_nursery = BehaviorNurseryImpl(nursery=n, dispatcher=pyctor.dispatch.single_process.SingleProcessDispatcher(nursery=n))
            nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        nursery.set(None)  # type: ignore


@asynccontextmanager
async def open_multiprocess_nursery(
    processes: int = multiprocessing.cpu_count(),
) -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            behavior_nursery = BehaviorNurseryImpl(nursery=n, dispatcher=pyctor.dispatch.multi_process.MultiProcessDispatcher(nursery=n, processes=processes))
            nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        nursery.set(None)  # type: ignore
