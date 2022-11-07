
from typing import Generic

from pyctor.types import T, Behavior, Context, LifecycleSignal



class MessageBehaviorInterceptor(Generic[T]):
    """
    Handles only messages of type T and ignores other messages
    """
    async def intercept(self, ctx: Context[T], msg: T | LifecycleSignal) -> Behavior[T]:
        pass

# async def receive_setup(ctx: "Context[T]") -> BehaviorFunction[T]:
#             async def receive_handler(
#                 ctx: "Context[T]", msg: T | LifecycleSignal
#             ) -> Behavior[T]:
#                 # only T messages are handled here, so match on that
#                 reveal_type(msg)
#                 match msg:
#                     case LifecycleSignal():
#                         return Behaviors.Same
#                     case _:
#                         return await func(msg)

#             return receive_handler