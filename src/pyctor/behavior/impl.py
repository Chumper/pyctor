from logging import getLogger
from typing import Type

import pyctor._util
import pyctor.behaviors
import pyctor.ref
import pyctor.signals
import pyctor.types

logger = getLogger(__name__)


class BehaviorHandlerImpl(pyctor.types.BehaviorHandler[pyctor.types.T]):
    """
    Class that all Behaviors need to implement if they want to be handled by Pyctor.
    This class fullfills the Protocol requirements.
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

    async def handle(
        self, msg: pyctor.types.T
    ) -> pyctor.types.Behavior[pyctor.types.T]:
        if self._type:
            # if the type is given, we assert on it here
            assert issubclass(type(msg), self._type), (
                "Can only handle messages derived from type "
                + str(self._type)
                + ", got "
                + str(type(msg))
            )
        return await self._behavior(msg)
