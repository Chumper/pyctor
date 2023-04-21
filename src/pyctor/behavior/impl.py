from logging import getLogger
from typing import Type

import pyctor.types

logger = getLogger(__name__)


class BehaviorHandlerImpl(pyctor.types.BehaviorFunctionHandler[pyctor.types.T]):
    """
    A behavior handler is a wrapper around a behavior function.
    It is used to handle messages of a specific type.
    Additionally, it can be used to check the type of the message.

    The behavior handler needs to be portable to other processes.

    """

    _behavior: pyctor.types.BehaviorFunction[pyctor.types.T]
    _type: Type[pyctor.types.T] | None = None

    def __init__(
        self,
        behavior: pyctor.types.BehaviorFunction[pyctor.types.T],
        type_check: Type[pyctor.types.T] | None = None,
    ) -> None:
        self._behavior = behavior
        self._type = type_check

    async def handle(self, msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
        if self._type:
            # if the type is given, we assert on it here
            assert issubclass(type(msg), self._type), f"Can only handle messages derived from type {str(self._type)} got {str(type(msg))}: {str(msg)}"
        return await self._behavior(msg)
