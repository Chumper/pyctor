
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

import trio

from pyctor.behaviors import Behaviors
from pyctor.types import Behavior, BehaviorGenerator, BehaviorHandler, BehaviorSetup, T


async def handle(msg: str) -> Behavior[str]:
    print(f"Received: {msg}")
    return Behaviors.Same

async def setup() -> BehaviorSetup[str]:
    yield Behaviors.receive(handle)

def test(func: Callable[[], BehaviorSetup[T]]) -> BehaviorGenerator[T]:
    
    @asynccontextmanager
    async def f() -> AsyncGenerator[BehaviorHandler[T], None]:
        async for f in func():
            async with f as t:
                yield t
    
    return f()

def cover(t: BehaviorGenerator[T]) -> BehaviorGenerator[T]:
    @asynccontextmanager
    async def f() -> AsyncGenerator[BehaviorHandler[T], None]:
        async with t as f:
            yield f
    
    return f()

async def main() -> None:
    t = Behaviors.receive(handle)
    setup_behavior = Behaviors.setup(setup)

    test_behavior = test(setup)

    async with t as b:
        await b.handle("test")

    async with test_behavior as b:
        await b.handle("test")

if __name__ == "__main__":
    trio.run(main)