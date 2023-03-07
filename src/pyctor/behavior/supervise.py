from logging import getLogger
from typing import Awaitable, Callable

import pyctor.behaviors
import pyctor.types

logger = getLogger(__name__)


class SuperviseBehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T]):
    """
    Will wrap a BehaviorHandler in a supervise strategy
    """

    _strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]]
    _behavior: pyctor.types.BehaviorHandler[pyctor.types.T]

    def __init__(
        self,
        strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]],
        behavior: pyctor.types.BehaviorHandler[pyctor.types.T],
    ) -> None:
        self._strategy = strategy
        self._behavior = behavior

    async def handle(self, msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
        try:
            return await self._behavior.handle(msg)
        except Exception as e:
            # run strategy
            return await self._strategy(e)
