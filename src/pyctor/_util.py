from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from types import FunctionType
from typing import AsyncGenerator, Callable


import pyctor.types


def to_contextmanager(
    behavior: Callable[
        [], _AsyncGeneratorContextManager[pyctor.types.Behavior[pyctor.types.T]]
    ]
    | pyctor.types.Behavior[pyctor.types.T],
) -> Callable[[],_AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]]]:
    match behavior:
        case pyctor.types.BehaviorHandler():

            @asynccontextmanager
            async def f() -> AsyncGenerator[
                pyctor.types.BehaviorHandler[pyctor.types.T], None
            ]:
                yield behavior

            return f
        case FunctionType():
            return behavior
        case _:
            raise ValueError(
                "behavior needs to implement the Behavior or the Generator Protocol"
            )
