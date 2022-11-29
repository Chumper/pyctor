import contextvars
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.dispatch
import pyctor.registry
import pyctor.spawn
import pyctor.types

registry = trio.lowlevel.RunVar("registry", pyctor.registry.BehaviorRegistry())
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
            nursery=nursery, dispatcher=options.dispatcher if options.dispatcher else pyctor.dispatch.SingleProcessDispatcher(nursery=nursery)
        )


@asynccontextmanager
async def open_nursery(
    options: pyctor.types.BehaviorNurseryOptions = pyctor.types.BehaviorNurseryOptions(),
) -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            behavior_nursery = BehaviorNurseryImpl(nursery=n, options=options)
            nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        nursery.set(None)  # type: ignore
