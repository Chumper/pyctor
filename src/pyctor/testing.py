import uuid
from typing import Callable, Generic, List, Type

from msgspec import Struct

import pyctor.types


class TestProbe(Generic[pyctor.types.T]):
    """
    A TestProbe can be used to check if certain messages were received.
    It will give access to the received messages for easier inspection.
    It also provides a ref so it can be passed around.

    IMPORTANT: The received messages are only available on the process that the TestProbe was created on.
    """

    ref: pyctor.types.Ref[pyctor.types.T]
    messages: List[pyctor.types.T]
    type: Type[pyctor.types.T]
    """
    The type of the messages that this TestProbe can receive.
    """

    def __init__(self, type: Type[pyctor.types.T], behavior_nursery: pyctor.types.BehaviorNursery) -> None:
        self.messages = []
        self.type = type
        self.behavior_nursery = behavior_nursery

    async def _init(self) -> None:
        # define the behavior
        async def handler(msg: pyctor.types.T) -> pyctor.types.Behavior[pyctor.types.T]:
            self.messages.append(msg)
            return pyctor.behaviors.Behaviors.Same

        behavior = pyctor.behaviors.Behaviors.receive(handler)

        # spawn the test probe behavior
        self.ref = await self.behavior_nursery.spawn(behavior=behavior, options={"name": f"testprobe/{uuid.uuid4()}"})

    # an init function that will take the type and the behavior nursery and returns a TestProbe, will also run the inital method on it
    @classmethod
    async def create(cls, type: Type[pyctor.types.T], behavior_nursery: pyctor.types.BehaviorNursery) -> "TestProbe":
        probe = cls(type=type, behavior_nursery=behavior_nursery)
        await probe._init()
        return probe
