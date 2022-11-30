from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable, Type

import pyctor._util
import pyctor.behavior
import pyctor.signals
import pyctor.types


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
        @asynccontextmanager
        async def f() -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            yield pyctor.behavior.BehaviorHandlerImpl(behavior=func, type_check=type_check)
        return f
    
    @staticmethod
    def setup(
        func: Callable[[], pyctor.types.BehaviorSetup[pyctor.types.T]],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        @asynccontextmanager
        async def f() -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            # hacky hack, not sure if correct
            async for f in func():
                async with f as t:
                    yield t
    
        return f

    @staticmethod
    def supervise(
        strategy: Callable[[Exception], Awaitable[pyctor.types.BehaviorSignal]],
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
    ) -> pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]:
        
        @asynccontextmanager
        async def f() -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            async with behavior() as f:
                yield pyctor.behavior.SuperviseBehaviorHandlerImpl(strategy=strategy, behavior=f)
        
        return f