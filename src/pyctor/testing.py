import uuid
from typing import Callable, List

import pyctor.types


class TestProbe(pyctor.types.Ref[pyctor.types.T]):
    """
    A TestProbe can be used as a Ref in the system.
    It will give access to the received messages for easier inspection.
    """

    messages: List[pyctor.types.T]
    url: str
    registry: str
    name: str

    def __init__(self) -> None:
        self.name = f"test-probe-{uuid.uuid4()}"
        self.url = f"test-probe://{self.name}"
        self.registry = "test-probe"
        self.messages: List[pyctor.types.T] = []

    def send(self, msg: pyctor.types.T) -> None:
        self.messages.append(msg)

    # implement the ask method of the Ref interface
    async def ask(
        self,
        f: Callable[
            [pyctor.types.Ref[pyctor.types.V]],
            pyctor.types.ReplyProtocol[pyctor.types.V],
        ],
    ) -> pyctor.types.V:
        raise NotImplementedError("TestProbe.ask is not implemented")

    # implement the stop method of the Ref interface
    def stop(self) -> None:
        # just return, the test probe is not a real behavior
        return
