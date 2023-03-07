from logging import getLogger
from typing import Any, Callable, Optional

import trio


import pyctor.behaviors
import pyctor.system
import pyctor.types

logger = getLogger(__name__)


class RefImpl(pyctor.types.Ref[pyctor.types.T]):
    strategy: pyctor.types.MessageStrategy
    """
    The strategy to use when messages should be send to this ref
    """
    registry: str
    """
    The url of the registry that the behavior behind this ref has been spawned in.
    Can be in the same process, on the same node in a different process or even on
    a remote node. 
    """
    name: str
    """
    The name of the behaviour, unique to its own registry, 
    but can be the same on different processes.
    """

    url: str
    """
    The combination of the registry and the name is the url
    """

    def __init__(self, registry: str, name: str, strategy: pyctor.types.MessageStrategy) -> None:
        super().__init__()
        self.registry = registry
        self.name = name
        self.url = self.registry + self.name
        self.strategy = strategy
    
    async def _internal_send(
        self,
        channel: trio.abc.SendChannel[pyctor.types.T],
        msg: pyctor.types.T,
        task_status=trio.TASK_STATUS_IGNORED,
    ) -> None:
        try:
            await channel.send(msg)
        except Exception:
            pass
            # logger.warning("Could not send message, Behavior already terminated")
        finally:
            task_status.started()

    async def ask(
        self,
        f: Callable[
            [pyctor.types.Ref[pyctor.types.V]],
            pyctor.types.ReplyProtocol[pyctor.types.V],
        ],
    ) -> pyctor.types.V:
        # spawn a new behavior that takes a V as message and then immediately stops
        response: pyctor.types.V
        # spawn behavior
        async def receive_behavior(
            msg: pyctor.types.V,
        ) -> pyctor.types.Behavior[pyctor.types.V]:
            nonlocal response
            response = msg
            return pyctor.behaviors.Behaviors.Stop

        async with pyctor.system.open_nursery() as n:
            reply_ref = await n.spawn(pyctor.behaviors.Behaviors.receive(receive_behavior))
            msg = f(reply_ref)
            # python has no intersection type...
            self.send(msg)  # type: ignore

        return response  # type: ignore
    
    def send(self, msg: pyctor.types.T) -> None:
        # get channel from registry
        registry: pyctor.types.Registry = pyctor.system.registry.get()
        channel = registry.channel_from_ref(self)
        # get nursery from context var
        msg = self.strategy.transform_send_message(self, msg)

        nursery = pyctor.system.nursery.get()
        if not nursery:
            raise RuntimeError("No nursery to send message")
        nursery._nursery.start_soon(self._internal_send, channel, msg)

    def stop(self) -> None:
        # get channel from registry
        registry: pyctor.types.Registry = pyctor.system.registry.get()
        channel: trio.abc.SendChannel = registry.channel_from_ref(self)

        msg = self.strategy.transform_stop_message(self)

        # get nursery from context var
        nursery = pyctor.system.nursery.get()
        if not nursery:
            raise RuntimeError("No nursery to send message")
        if msg:
            nursery._nursery.start_soon(self._internal_send, channel, msg)
        else:
            # close the sending channel
            nursery._nursery.start_soon(channel.aclose)