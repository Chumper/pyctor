from logging import getLogger
from typing import Callable, Type, cast

import trio

import pyctor.behavior
import pyctor.signals
import pyctor.system
import pyctor.types

logger = getLogger(__name__)


class LocalRef(pyctor.types.Ref[pyctor.types.T]):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    async def _internal_send(self, channel: trio.abc.SendChannel[pyctor.types.T], msg: pyctor.types.T, task_status=trio.TASK_STATUS_IGNORED) -> None:
        try:
            await channel.send(msg)
        except trio.ClosedResourceError:
            logger.warning("Could not send message, Behavior already terminated")
        finally:
            task_status.started()

    def send(self, msg: pyctor.types.T) -> None:
        # get channel from registry
        channel = pyctor.system.registry.get().get(self)
        # get nursery from context var
        nursery = pyctor.system.nursery.get()
        if not nursery:
            raise RuntimeError("No nursery to send message")
        nursery.start_soon(self._internal_send, channel, msg)

    async def ask(
        self,
        f: Callable[
            [pyctor.types.Ref[pyctor.types.V]],
            pyctor.types.ReplyProtocol[pyctor.types.V],
        ],
    ) -> pyctor.types.V:
        # spawn a new behavior that takes a V as message and then immediately stops
        response: pyctor.types.V
        async with pyctor.system.open_nursery() as n:
            # spawn behavior
            async def receive_behavior(
                msg: pyctor.types.V,
            ) -> pyctor.types.Behavior[pyctor.types.V]:
                nonlocal response
                response = msg
                return pyctor.behavior.Behaviors.Stop

            reply_ref = await n.spawn(pyctor.behavior.BehaviorHandlerImpl(behavior=receive_behavior))
            await self.send(f(reply_ref))
        return response

    async def stop(self) -> None:
        # get channel from registry
        channel = pyctor.system.registry.get().get(self)

        # close the sending channel
        await channel.aclose()

    def address(self) -> str:
        return self.url

    def unsafe_cast(self, clazz: Type[pyctor.types.U]) -> pyctor.types.Ref[pyctor.types.U]:
        return cast(pyctor.types.Ref[pyctor.types.U], self)
