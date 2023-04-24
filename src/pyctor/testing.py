import uuid
from typing import Callable, Generic, List, Type

import trio
from msgspec import Struct

import pyctor.types


class TestProbe(Generic[pyctor.types.T]):
    """
    A TestProbe can be used to check if a single message was received.
    It will give access to the received message for easier inspection with a wait method.
    It also provides a ref so it can be passed around.

    IMPORTANT: The received message is only available on the process that the TestProbe was created on.
    """

    ref: pyctor.types.Ref[pyctor.types.T]
    message: pyctor.types.T | None = None
    type: Type[pyctor.types.T]
    event: trio.Event = trio.Event()

    def __init__(
        self, type: Type[pyctor.types.T], behavior_nursery: pyctor.types.BehaviorNursery
    ) -> None:
        self.message = None
        self.type = type
        self.behavior_nursery = behavior_nursery

    async def _init(self) -> None:
        # define the behavior
        async def handler(msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
            # assign the message
            self.message = msg
            # set the event
            self.event.set()
            # stop the behavior as we only want to receive one message
            return pyctor.behaviors.Behaviors.Stop

        behavior = pyctor.behaviors.Behaviors.receive(handler)

        # spawn the test probe behavior
        self.ref = await self.behavior_nursery.spawn(
            behavior=behavior, options={"name": f"testprobe/{uuid.uuid4()}"}
        )

    # an init function that will take the type and the behavior nursery and returns a TestProbe, will also run the inital method on it
    @classmethod
    async def create(
        cls, type: Type[pyctor.types.T], behavior_nursery: pyctor.types.BehaviorNursery
    ) -> "TestProbe":
        """
        Create a new TestProbe that is able to receive a single message of the given type.
        The returned TestProbe has a ref that can be used to send messages to or to pass to other parts of the system.
        Offers a `wait` method that will wait until a message has been received and return it.
        """
        probe = cls(type=type, behavior_nursery=behavior_nursery)
        await probe._init()
        return probe

    async def wait(self) -> pyctor.types.T:
        """
        Wait until a message has been received and return it.
        """
        await self.event.wait()
        if self.message is None:
            raise Exception("No message was received")
        return self.message
