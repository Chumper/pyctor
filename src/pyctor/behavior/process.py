from logging import getLogger
from types import FunctionType
from typing import Generic

import trio
import typeguard
from typeguard import check_type

import pyctor._util
import pyctor.behaviors
import pyctor.context
import pyctor.ref
import pyctor.signals
import pyctor.system
import pyctor.types

logger = getLogger(__name__)


class BehaviorProcessorImpl(pyctor.types.BehaviorProcessor, Generic[pyctor.types.T]):
    """
    The BehaviorProcessor is the main entry point for the behavior system.
    It is responsible for the creation of the behavior tasks and the
    communication between the behavior and the actor.
    """

    _channel: trio.abc.ReceiveChannel[pyctor.types.T]
    """
    The incoming channel for messages.
    """

    _behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]
    """
    The behavior function, in essence the business logic of the behavior.
    """

    _context: pyctor.types.Context[pyctor.types.T]
    """
    The context for the behavior.
    """

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
            # get a local reference to the behavior
            behavior = self._behavior
            # run the behavior until it is stopped, indicated by the run flag
            run = True
            while run:
                try:
                    # for each new behavior, verify the type
                    check_type(behavior, pyctor.types.BehaviorGeneratorFunction[pyctor.types.T])  # type: ignore

                    async with behavior(self._context) as b:
                        try:
                            while True:
                                # receive a message from the channel
                                msg = await self._channel.receive()
                                # handle the message with the behavior
                                new_behavior = await b.handle(msg)
                                # check the type of the new behavior
                                match new_behavior:
                                    # message has not been handled
                                    case pyctor.behaviors.Behaviors.Ignore:
                                        logger.warning("Ignoring message: %s", type(msg))
                                    # behavior has not changed
                                    case pyctor.behaviors.Behaviors.Same:
                                        pass
                                    # behavior has been stopped
                                    case pyctor.behaviors.Behaviors.Stop:
                                        # close the channel
                                        await self._channel.aclose()
                                        # stop the behavior, this will exit the loop on the next iteration
                                        run = False
                                        break
                                    # behavior has been restarted
                                    case pyctor.behaviors.Behaviors.Restart:
                                        # restart the behavior, breaking will reevaluate the behavior
                                        break
                                    # behavior has been changed
                                    case FunctionType():
                                        # check the type of the new behavior
                                        check_type(
                                            new_behavior,
                                            pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],  # type: ignore
                                        )
                                        behavior = new_behavior
                                        # break the loop to reevaluate the behavior
                                        break
                        except (trio.EndOfChannel, trio.ClosedResourceError):
                            # Channel has been closed, behavior should be stopped
                            # catch exception to enable teardown of behavior
                            run = False
                except (TypeError, typeguard.TypeCheckError) as t:
                    # Behavior or chain has not the correct type.
                    # Abort in this case with an error message and stop
                    logger.error("Behavior has not the correct type: %s", t)
                    run = False
        finally:
            pass
