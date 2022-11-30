from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from types import FunctionType, MethodType
from typing import Any, AsyncContextManager, AsyncGenerator, Callable

import pytypes.type_util

import pyctor.behavior
import pyctor.types


def is_generator(to_test: Any) -> bool:
    if pytypes.type_util._isinstance(to_test, pyctor.types.BehaviorGeneratorFunction):
        return True
    return False