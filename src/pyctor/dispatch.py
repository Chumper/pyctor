import trio

import pyctor.behavior
import pyctor.behavior.process
import pyctor.system
import pyctor.types


class SingleProcessDispatcher(pyctor.types.Dispatcher):
    """
    Dispatcher that will start the Behavior in the current existing trio nursery.
    Effectively it will start each Behavior in the same process tree as this nursery.
    """

    _nursery: trio.Nursery

    def __init__(self, nursery: trio.Nursery) -> None:
        super().__init__()
        self._nursery = nursery

    async def dispatch(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        name: str,
    ) -> pyctor.types.Ref[pyctor.types.T]:
        # define channels
        send: trio.abc.SendChannel
        receive: trio.abc.ReceiveChannel

        # create a new memry channel
        send, receive = trio.open_memory_channel(0)
        # register and get ref
        ref = pyctor.system.registry.get().register(name=name, channel=send)

        # create the process
        b = pyctor.behavior.process.BehaviorProcessorImpl[pyctor.types.T](behavior=behavior, channel=receive, self_ref=ref)

        # start in the nursery
        self._nursery.start_soon(b.behavior_task)

        # return the ref
        return ref


# class MultiProcessDispatcher(pyctor.types.Dispatcher):
#     """
#     Dispatcher that will start the Behavior in the current existing trio nursery.
#     Effectively it will start each Behavior in the same process tree as this nursery.
#     """

#     _nursery: trio.Nursery

#     def __init__(self, nursery: trio.Nursery) -> None:
#         super().__init__()
#         self._nursery = nursery

#     async def dispatch(
#         self,
#         behavior: Callable[
#             [],
#             _AsyncGeneratorContextManager[pyctor.types.BehaviorHandler[pyctor.types.T]],
#         ],
#         name: str,
#     ) -> pyctor.types.Ref[pyctor.types.T]:
#         # create the process
#         b = pyctor.behavior.BehaviorProcessorImpl[pyctor.types.T](
#             nursery=self._nursery,
#             behavior=behavior,
#             name=name,
#         )
#         # start in the nursery
#         self._nursery.start_soon(b.behavior_task)
#         return b.ref()
