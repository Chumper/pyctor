from logging import getLogger
from types import FunctionType
from typing import Generic

import trio

import pyctor._util
import pyctor.behaviors
import pyctor.ref
import pyctor.signals
import pyctor.types
import pyctor.system

logger = getLogger(__name__)


class BehaviorProcessorImpl(pyctor.types.BehaviorProcessor, Generic[pyctor.types.T]):
    _channel: trio.abc.ReceiveChannel[pyctor.types.T]
    _behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]
    _context: pyctor.types.Context[pyctor.types.T]

    def __init__(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        channel: trio.abc.ReceiveChannel[pyctor.types.T],
        context: pyctor.types.Context[pyctor.types.T],
    ) -> None:
        super().__init__()
        self._channel = channel
        self._behavior = behavior
        self._context = context

    async def behavior_task(self) -> None:
        """
        The main entry point for each behavior and therefore each task.
        This method is a single task in the trio concept.
        Everything below this Behavior happens in this task.
        """
        try:
            behavior = self._behavior
            run = True
            while run:
                try:
                    if not isinstance(behavior, FunctionType):  # pragma: no cover
                        logger.error(
                            f"The provided behavior has an incorrect type: {type(behavior)}"
                        )
                        raise TypeError(behavior)
                    async with behavior(self._context) as b:
                        if not isinstance(
                            b, pyctor.types.BehaviorHandler
                        ):  # pragma: no cover
                            logger.error(
                                f"The provided behavior has an incorrect type: {type(b)}"
                            )
                            raise TypeError(b)
                        try:
                            while True:
                                msg = await self._channel.receive()
                                new_behavior = await b.handle(msg)
                                match new_behavior:
                                    case pyctor.behaviors.Behaviors.Ignore:
                                        logger.warning("Ignoring message: %s", type(msg))
                                    case pyctor.behaviors.Behaviors.Same:
                                        pass
                                    case pyctor.behaviors.Behaviors.Stop:
                                        await self._channel.aclose()
                                        run = False
                                        break
                                    case pyctor.behaviors.Behaviors.Restart:
                                        # restart the behavior
                                        break
                                    case FunctionType():
                                        # trust our asserts here...
                                        behavior = new_behavior
                                        break
                        except (trio.EndOfChannel, trio.ClosedResourceError):
                            # Channel has been closed, behavior should be stopped
                            # catch exception to enable teardown of behavior
                            run = False
                except TypeError as t:
                    # Behavior or chain has not the correct type.
                    # Abort in this case with an error message and stop
                    logger.error("Behavior has not the correct type: %s", t)
                    run = False
        finally:
            # unregister the ref in the registry
            # TODO: Should be somewhere else...
            registry: pyctor.types.Registry = pyctor.system.registry.get()
            await registry.deregister(self._context.self())
