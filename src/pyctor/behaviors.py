from contextlib import asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncContextManager, AsyncGenerator, Awaitable, Callable, Type

from typeguard import check_type

import pyctor._util
import pyctor.behavior
import pyctor.behavior.impl
import pyctor.behavior.supervise
import pyctor.signals
import pyctor.types

logger = getLogger(__name__)


class Behaviors:
    Same: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(1)
    """
    Indicates that the Behavior should stay the same for the next message.
    """

    Stop: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(2)
    """
    Indicates that the Behavior should be stopped.
    No messages are handled after the current one.
    """

    Restart: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(3)
    """
    Indicates that a Behavior should be restarted. 
    That means that the setup (if available) of the Behavior will be executed again.
    """

    Ignore: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(4)
    """
    Indicates that the message was not handled and has should be ignored. 
    Will emit a warning.
    """

    @staticmethod
    def receive(
        func: pyctor.types.BehaviorFunction[pyctor.types.T],
        type_check: Type[pyctor.types.T] | None = None,
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        """
        Creates a Behavior that will handle messages of type T.
        The behavior function will be called with the message as argument.
        The behavior function must return a Behavior[T] or a BehaviorSignal.
        """
        # check if the function is of type BehaviorFunction[T]
        check_type(func, pyctor.types.BehaviorFunction[pyctor.types.T])  # type: ignore

        @asynccontextmanager
        async def f(
            _: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorFunctionHandler[pyctor.types.T], None]:
            yield pyctor.behavior.impl.BehaviorHandlerImpl(behavior=func, type_check=type_check)

        return f

    @staticmethod
    def setup(
        func: Callable[
            [pyctor.types.Context[pyctor.types.T]],
            pyctor.types.BehaviorSetup[pyctor.types.T],
        ],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        """
        Will create a Behavior that will run the given function as setup.
        The setup function must return a BehaviorSetup[T] which is an async generator.
        The setup function will be called with the context as argument.
        The setup function must yield a BehaviorFunctionHandler[T] which is a function that will be called with the message as argument.
        """

        # check that the given function is of type BehaviorSetup[T]
        check_type(
            func,
            Callable[
                [pyctor.types.Context[pyctor.types.T]],
                pyctor.types.BehaviorSetup[pyctor.types.T],
            ],
        )

        # create a BehaviorGeneratorFunction[T] from the given function
        # this is a bit ugly because we only get an async generator from the given function
        # but we need to return a BehaviorGeneratorFunction[T] which is an async context manager.
        # As we do not want to burden the user with creating/annotationg the async context manager
        # we create it here on our own.
        @asynccontextmanager
        async def f(
            c: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorFunctionHandler[pyctor.types.T], None]:
            # get the first BehaviorGeneratorFunction from the setup function
            # this will execute the custom setup function
            async for f in func(c):
                # we now have a BehaviorGeneratorFunction[T]
                m = f(c)
                # we now have a BehaviorFunctionHandler[T]
                async with m as t:
                    # we now have a BehaviorFunction[T]
                    yield t

        # return the BehaviorGeneratorFunction[T]
        return f

    @staticmethod
    def supervise(
        strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]],
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        """
        Will wrap the already existing BehaviorGeneratorFunction[T] with a supervisor.
        If an exception is raised in the BehaviorGeneratorFunction[T] the supervisor will be called with the exception.
        The supervisor must return a BehaviorSignal.
        """

        @asynccontextmanager
        async def f(
            c: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorFunctionHandler[pyctor.types.T], None]:
            # type check the strategy and behavior
            check_type(strategy, Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]])
            check_type(behavior, pyctor.types.BehaviorGeneratorFunction[pyctor.types.T])  # type: ignore

            async with behavior(c) as f:
                # we now have a BehaviorFunctionHandler[T]
                # wrap it in a customr SupervisorBehaviorHandler
                yield pyctor.behavior.supervise.SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=f)

        return f
