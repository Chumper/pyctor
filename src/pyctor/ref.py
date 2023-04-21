import os
import uuid
from logging import getLogger
from typing import Any, Callable, Optional

import trio

import pyctor.behaviors
import pyctor.system
import pyctor.types

logger = getLogger(__name__)


class RefImpl(pyctor.types.Ref[pyctor.types.T]):
    """
    A ref implementation that is used for local and remote refs.
    This is the main reference that is being used in the system.
    """

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

    _registry: pyctor.types.Registry
    """
    The registry that this ref is registered with in this process.
    This can be the the registry that spawned the underlying behavior (for local refs)
    or it is a registry that can handle messages for this ref to the original process (for remote refs).
    """

    def __init__(
        self,
        registry: str,
        name: str,
        strategy: pyctor.types.MessageStrategy,
        managing_registry: pyctor.types.Registry,
    ) -> None:
        """
        Create a new ref.
        Accepts a registry url, a name and a message strategy.
        """
        super().__init__()
        self.registry = registry
        self.name = name
        self.url = self.registry + self.name
        self.strategy = strategy
        self._registry = managing_registry

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
            reply_ref = await n.spawn(
                pyctor.behaviors.Behaviors.receive(receive_behavior),
                options={
                    "name": f"ask-{uuid.uuid4()}",
                },
            )
            msg = f(reply_ref)
            # python has no intersection type...
            self.send(msg)  # type: ignore

        return response  # type: ignore

    def send(self, msg: pyctor.types.T) -> None:

        msg = self.strategy.transform_send_message(self, msg)

        # get nursery from context var
        nursery = pyctor.system.nursery.get()
        if not nursery:
            raise RuntimeError("No nursery to send message")

        # get channel from registry
        channel: trio.abc.SendChannel = self._registry.channel_from_ref(self)
        nursery._nursery.start_soon(self._internal_send, channel, msg)

    def stop(self) -> None:
        msg = self.strategy.transform_stop_message(self)

        # get nursery from context var
        nursery = pyctor.system.nursery.get()
        if not nursery:
            raise RuntimeError("No nursery to send message")
        # get channel from registry
        channel: trio.abc.SendChannel = self._registry.channel_from_ref(self)
        if msg:
            nursery._nursery.start_soon(self._internal_send, channel, msg)
        else:
            # close the sending channel
            nursery._nursery.start_soon(channel.aclose)


class SystemRefImpl(pyctor.types.Ref[pyctor.types.T]):
    """
    A ref implementation that is as a special case for the system ref.
    A system ref is only known to the process it is created in and is not registered in any registry.
    The creator of the ref is responsible for cleaning up the ref and all resources associated with it.
    The system ref is tied to a specific channel and can only be used in the process it was created in.
    """

    registry: str = "system-ref"
    name: str
    url: str = "system-url"

    _channel: trio.abc.SendChannel[pyctor.types.T]
    """
    The channel that this ref is tied to.
    """
    _nursery: trio.Nursery
    """
    The nursery that this ref is tied to.
    """

    def __init__(
        self,
        name: str,
        channel: trio.abc.SendChannel[pyctor.types.T],
        nursery: trio.Nursery,
    ) -> None:
        super().__init__()
        self.name = name
        self.url = self.registry + self.name
        self._channel = channel
        self._nursery = nursery

    async def _internal_send(
        self,
        msg: pyctor.types.T,
        task_status=trio.TASK_STATUS_IGNORED,
    ) -> None:
        try:
            await self._channel.send(msg)
        except Exception:
            pass
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
            reply_ref = await n.spawn(
                pyctor.behaviors.Behaviors.receive(receive_behavior),
                options={
                    "name": f"ask-{uuid.uuid4()}",
                },
            )
            msg = f(reply_ref)
            # python has no intersection type...
            self.send(msg)  # type: ignore

        return response  # type: ignore

    def send(self, msg: pyctor.types.T) -> None:
        self._nursery.start_soon(self._internal_send, msg)

    def stop(self) -> None:
        # close the sending channel
        self._nursery.start_soon(self._channel.aclose)
