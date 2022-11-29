from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from types import FunctionType, MethodType
from typing import AsyncGenerator, Callable

import pyctor.types


def to_contextmanager(
    behavior: Callable[[], _AsyncGeneratorContextManager[pyctor.types.Behavior[pyctor.types.T]]] | pyctor.types.Behavior[pyctor.types.T],
) -> Callable[[], _AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]]]:
    if isinstance(behavior, pyctor.types.BehaviorHandler):

        @asynccontextmanager
        async def f() -> AsyncGenerator[pyctor.types.BehaviorHandler[pyctor.types.T], None]:
            yield behavior

        return f
    elif isinstance(behavior, FunctionType) or isinstance(behavior, MethodType):
        return behavior
    else:
        raise ValueError("behavior needs to implement the Behavior or the Generator Protocol")
