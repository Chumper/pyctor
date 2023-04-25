from uuid import uuid4

import trio

import pyctor.behavior
import pyctor.behavior.process
import pyctor.context
import pyctor.ref
import pyctor.system
import pyctor.types


class SingleProcessDispatcher(pyctor.types.Dispatcher):
    """
    Dispatcher that will start new behaviors in the current existing trio nursery.
    Effectively it will start each Behavior in the same process as this process.
    """

    _nursery: trio.Nursery
    """
    The nursery that will be used to spawn new behaviors.
    """
    _registry: pyctor.types.Registry
    """
    The registry that will be used to register new behaviors.
    """

    def __init__(self, nursery: trio.Nursery, registry: pyctor.types.Registry) -> None:
        """
        Initialize the dispatcher.
        """
        super().__init__()
        self._nursery = nursery
        self._registry = registry

    async def dispatch(
        self,
        behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
        options: pyctor.types.SpawnOptions | None,
    ) -> pyctor.types.Ref[pyctor.types.T]:

        if not options:
            options = {}

        # check if name is set
        if not options.get("name"):
            options["name"] = str(uuid4())
        # check if buffer size is set
        if not options.get("buffer_size"):
            options["buffer_size"] = 0

        # define channels
        send: trio.abc.SendChannel
        receive: trio.abc.ReceiveChannel

        # create a new memory channel
        send, receive = trio.open_memory_channel(options["buffer_size"])

        # register and get ref
        ref = await self._registry.register(name=options["name"], channel=send)

        # create the context
        context = pyctor.context.ContextImpl(ref=ref)

        # create the process
        b = pyctor.behavior.process.BehaviorProcessorImpl[pyctor.types.T](
            behavior=behavior, channel=receive, context=context
        )

        # start in the nursery
        self._nursery.start_soon(self._behavior_lifecycle_task, b, ref)

        # return the ref
        return ref

    async def _behavior_lifecycle_task(
        self,
        behavior_process: pyctor.types.BehaviorProcessor,
        ref: pyctor.types.Ref[pyctor.types.T],
    ) -> None:
        """
        Async task to handle the lifecycle of the behavior.
        Only here to make sure the behavior gets deregisterd from the registry.
        """
        try:
            await behavior_process.behavior_task()
        finally:
            await self._registry.deregister(ref)


async def spawn_system_behavior(
    behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T],
    options: pyctor.types.SpawnOptions,
    nursery: trio.Nursery,
) -> pyctor.ref.SystemRefImpl[pyctor.types.T]:
    """
    Spawn a new behavior without a registry in this process.
    The behavior is the considered a system behavior and the caller is responsible to terminate the system behavior.
    Accepts a trio nursery where the behavior will be spawned.
    """

    # define channels
    send: trio.abc.SendChannel
    receive: trio.abc.ReceiveChannel

    # create a new memory channel
    send, receive = trio.open_memory_channel(options["buffer_size"])

    # create a new system ref
    ref = pyctor.ref.SystemRefImpl(
        name=options["name"],
        channel=send,
        nursery=nursery,
    )

    # create the context
    context = pyctor.context.ContextImpl(ref=ref)

    # create the process
    b = pyctor.behavior.process.BehaviorProcessorImpl[pyctor.types.T](
        behavior=behavior, channel=receive, context=context
    )

    # start in the nursery
    nursery.start_soon(b.behavior_task)

    # return the ref
    return ref
