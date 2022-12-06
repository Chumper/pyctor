import contextvars
import multiprocessing
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.dispatch.multi_process
import pyctor.dispatch.single_process
import pyctor.spawn
import pyctor.types
from pyctor.registry import BehaviorRegistry

registry: trio.lowlevel.RunVar = trio.lowlevel.RunVar("registry", BehaviorRegistry())
"""
trio.run local registry for all behaviors. Effectively one core.
"""
nursery = contextvars.ContextVar[pyctor.types.BehaviorNursery]("nursery")
"""
Context var for each nursery. Is used by the refs to schedule a send in the current nursery
"""


class BehaviorNurseryImpl(pyctor.spawn.SpawnerImpl, pyctor.types.BehaviorNursery):
    def __init__(self, nursery: trio.Nursery, options: pyctor.types.BehaviorNurseryOptions) -> None:
        super().__init__(
            nursery=nursery,
            dispatcher=options.dispatcher if options.dispatcher else pyctor.dispatch.single_process.SingleProcessDispatcher(nursery=nursery),
        )


@asynccontextmanager
async def open_nursery() -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            options = pyctor.types.BehaviorNurseryOptions(dispatcher=pyctor.dispatch.single_process.SingleProcessDispatcher(nursery=n))
            behavior_nursery = BehaviorNurseryImpl(nursery=n, options=options)
            nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        nursery.set(None)  # type: ignore


@asynccontextmanager
async def open_multiprocess_nursery(
    cores: int = multiprocessing.cpu_count(),
) -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            options = pyctor.types.BehaviorNurseryOptions(dispatcher=pyctor.dispatch.multi_process.MultiProcessDispatcher(nursery=n, processes=cores))
            behavior_nursery = BehaviorNurseryImpl(nursery=n, options=options)
            nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        nursery.set(None)  # type: ignore
