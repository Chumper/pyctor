import contextvars
import multiprocessing
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import trio

import pyctor.dispatch.multi_process
import pyctor.dispatch.single_process
import pyctor.registry
import pyctor.spawn
import pyctor.types

registry: trio.lowlevel.RunVar = trio.lowlevel.RunVar(name="registry", default=pyctor.registry.RegistryImpl())  # type: ignore
"""
trio.run local registry for all behaviors. Effectively one core.
"""
nursery = contextvars.ContextVar[pyctor.types.BehaviorNursery]("nursery")
"""
Context var for each nursery. Is used by the refs to schedule a send in the current nursery
"""


class BehaviorNurseryImpl(pyctor.spawn.SpawnerImpl, pyctor.types.BehaviorNursery):
    def __init__(
        self, nursery: trio.Nursery, dispatcher: pyctor.types.Dispatcher
    ) -> None:
        super().__init__(
            nursery=nursery,
            dispatcher=dispatcher,
        )


@asynccontextmanager
async def open_nursery(
    processes: int = 1,
) -> AsyncGenerator[pyctor.types.BehaviorNursery, None]:
    try:
        async with trio.open_nursery() as n:
            # get registry from run var
            reg = registry.get()
            # set single process dispatcher if processes == 1
            dispatcher = (
                pyctor.dispatch.single_process.SingleProcessDispatcher(
                    nursery=n, registry=reg
                )
                if processes == 1
                else pyctor.dispatch.multi_process.MultiProcessDispatcher(
                    nursery=n,
                    processes=processes,
                    dispatcher=pyctor.dispatch.single_process.SingleProcessDispatcher(
                        nursery=n, registry=reg
                    ),
                )
            )
            behavior_nursery = BehaviorNurseryImpl(
                nursery=n,
                dispatcher=dispatcher,
            )
            token = nursery.set(behavior_nursery)
            yield behavior_nursery
    finally:
        # nursery.reset(token)  # type: ignore
        pass
