from contextlib import asynccontextmanager
from logging import getLogger
from types import FunctionType
from typing import AsyncContextManager, AsyncGenerator, Awaitable, Callable, Type

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
    Indicates that the Behavior wants to be stopped. 
    A Behavior will get a final 'Stopped' LifecycleSignal and will then be terminated.
    """

    Restart: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(3)
    """
    Indicates that a Behavior wants to be restarted. 
    That means that the Behavior receives a 'Stopped' and then 'Started' LifecycleSignal.
    Also means that the setup (if available) of the Behavior will be executed again.
    """

    Ignore: pyctor.types.BehaviorSignal = pyctor.signals.BehaviorSignalImpl(4)
    """
    Indicates that the message was not handled and ignored. Will emit a warning
    """

    @staticmethod
    def receive(
        func: pyctor.types.BehaviorFunction[pyctor.types.T],
        type_check: Type[pyctor.types.T] | None = None,
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        if not isinstance(func, FunctionType):
            logger.error(f"Behaviors.receive() was not provided a BehaviorFunction[T]): {type(func)}")
            raise TypeError(func)

        @asynccontextmanager
        async def f(
            c: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            yield pyctor.behavior.impl.BehaviorHandlerImpl(behavior=func, type_check=type_check)

        return f

    @staticmethod
    def setup(
        func: Callable[
            [pyctor.types.Context[pyctor.types.T]],
            pyctor.types.BehaviorSetup[pyctor.types.T],
        ],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        # if not isinstance(func, Callable[[pyctor.types.Context[pyctor.types.T]], pyctor.types.BehaviorSetup[pyctor.types.T]]):
        #     logger.error(f"Behaviors.setup() was not provided () -> BehaviorSetup[T]): {type(func)}")
        #     raise TypeError(func)

        @asynccontextmanager
        async def f(
            c: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            async for f in func(c):
                # if not isinstance(f, Callable[[str],None]):
                #     logger.error(f"Behaviors.setup() was not provided () -> BehaviorSetup[T]): {type(f)}")
                #     raise TypeError(f)
                m = f(c)
                # if not isinstance(m, AsyncContextManager):
                #     logger.error(f"Behaviors.setup() was not provided () -> BehaviorSetup[T]): {type(m)}")
                #     raise TypeError(m)
                async with m as t:
                    # if not isinstance(t, pyctor.types.BehaviorHandler):
                    #     logger.error(f"Behaviors.setup() was not provided () -> BehaviorSetup[T]): {type(t)}")
                    #     raise TypeError(t)
                    yield t

        return f

    @staticmethod
    def supervise(
        strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]],
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        @asynccontextmanager
        async def f(
            c: pyctor.types.Context[pyctor.types.T],
        ) -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            async with behavior(c) as f:
                # if not isinstance(f, pyctor.types.BehaviorHandler):
                #     logger.error(f"Behaviors.supervise() was not provided () -> BehaviorGenerator[T]): {type(f)}")
                #     raise TypeError(f)
                yield pyctor.behavior.supervise.SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=f)

        return f
