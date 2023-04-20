import platform
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple

import trio

import pyctor.message_strategies
import pyctor.ref
import pyctor.types

logger = getLogger(__name__)


class RegistryImpl(pyctor.types.Registry):
    """
    A registry that contains the channels for each behavior in this process.
    The registry is unique for each process and can be used in a thread safe way to
    get channels for registered behaviors.
    """

    @dataclass
    class WatcherEntry:
        """
        A watcher entry contains a ref to a behavior and a message that should be sent to that behavior in case the ref is terminated.
        """

        ref: pyctor.types.Ref[Any]
        """
        The ref to the behavior that should be called in case the ref that this entry belongs to is terminated.
        """
        msg: Any
        """
        The message that should be sent to the behavior.
        """

    url: str
    """
    The unique address of this registry
    """
    _lock: trio.Lock = trio.Lock()
    """
    A lock to guarantee safe access to the registry data
    """
    _registry: Dict[str, Tuple[pyctor.types.Ref[Any], trio.abc.SendChannel]] = {}
    """
    Heart of the registry, contains all registered refs and their channels.
    """
    _watchers: Dict[str, List[WatcherEntry]] = {}
    """
    Contains all behaviors in this process that want to watch other refs.
    It could be that a behavior wants to watch a ref in another process.
    It is important to know that this will only hold watchers in this process.
    Other registries could watch the same behavior just with different watchers. 
    """
    _remotes: Dict[str, trio.abc.SendChannel] = {}
    """
    Contains all remote registries that are linked to this registry.
    """
    _fallback: Optional[trio.abc.SendChannel] = None
    """
    A fallback channel that is used when a ref is not available in this registry.
    If None, then a send will raise an exception.
    Can be used to implement a dead letter channel 
    or a default parent registry that should handle the message.
    """

    def __init__(
        self,
        name: str = f"{platform.node().lower()}/0",
        fallback: Optional[trio.abc.SendChannel] = None,
    ):
        """
        Create a new registry.
        Accepts a name for this registry. This is used to create a unique url for this registry.
        Accepts a fallback channel. This is used to send messages to a remote registry.
        """
        self.url = f"pyctor://{name}/"
        self._fallback = fallback

    async def watch(
        self,
        ref: pyctor.types.Ref[pyctor.types.T],
        watcher: pyctor.types.Ref[pyctor.types.U],
        msg: pyctor.types.U,
    ) -> None:
        """
        Watch a ref. If the ref is available, then the watcher will be added to a list of watchers.
        If the ref is unavailable, then the watcher will be called immediately with the given message.
        A ref can be unavailable if it is not present in this registry or if it has been terminated.
        """
        # add to watchers if available, send to ref immediately if not
        async with self._lock:
            if ref.url in self._watchers:
                # add to watcher
                self._watchers[ref.url].append(RegistryImpl.WatcherEntry(ref=watcher, msg=msg))
            else:
                # if the ref does not exist in this registry,
                # then we send the message to the watcher immediately
                watcher.send(msg=msg)

    async def deregister(self, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        """
        Deregister a ref. If the ref is available, then all watchers will be called with the message attached to the watcher.
        Will also send a stopped message to all remotes if the ref is owned by this registry.
        """
        # remove from dict and call watchers
        async with self._lock:
            if ref.url in self._registry:
                channel = self.channel_from_ref(ref=ref)
                logger.debug(f"Deregister ref: {ref.url}")

                # available, so call watchers and remove from dict
                for entry in self._watchers[ref.url]:
                    entry.ref.send(entry.msg)

                # remove if this is the fallback channel
                if self._fallback == channel:
                    self._fallback = None

                # remove from remotes if this is a remote channel
                for reg, chan in self._remotes.items():
                    if chan == channel:
                        del self._remotes[reg]
                        break

                # if we own this behavior, then we send a stopped message to all remotes
                if ref.registry == self.url:
                    msg = pyctor.types.StoppedEvent(ref=ref)
                    # send to fallback if available
                    if self._fallback:
                        await self._fallback.send(msg)

                    # send to all remotes
                    for r in self._remotes.values():
                        await r.send(msg)

                # finally remove from dict
                del self._registry[ref.url]

    async def register(
        self,
        name: str,
        channel: trio.abc.SendChannel[pyctor.types.T],
    ) -> pyctor.types.Ref[pyctor.types.T]:
        """
        Accepts a name which is used to identify the channel in this registry.
        Raises a ValueError if the name is already registered.
        Returns a ref that can be used to send messages to.
        """
        async with self._lock:
            if self.url + name in self._registry:
                raise ValueError(f"Name '{name}' is already registered")
            self._registry[self.url + name] = (
                pyctor.ref.RefImpl(
                    registry=self.url,
                    name=name,
                    strategy=pyctor.message_strategies.LOCAL,
                    managing_registry=self,
                ),
                channel,
            )
            self._watchers[self.url + name] = []
        return self._registry[self.url + name][0]

    async def register_remote(self, registry: str, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        """
        Register a remote ref. This is used to register a ref that is owned by another registry.
        Raises a ValueError if the ref is already registered.
        """
        async with self._lock:
            if ref.url in self._registry:
                raise ValueError(f"Ref '{ref.url}' is already registered")
            self._remotes[registry] = self.channel_from_ref(ref)

    def ref_from_raw(self, registry: str, name: str) -> pyctor.types.Ref[pyctor.types.T]:
        """
        Create a ref from a raw registry and name.
        Mainly used when a ref is received from a the wire e.g. msgpack."""
        if registry == self.url and registry + name in self._registry:
            logger.debug("Returning LocalRef from wire: %s%s", registry, name)
            return self._registry[registry + name][0]
        elif registry != self.url and registry + name in self._registry:
            logger.debug("Returning RemoteRef from wire: %s%s", registry, name)
            return self._registry[registry + name][0]
        else:
            try:
                self._lock.acquire_nowait()
                default_remote = self._default_remote if self._default_remote else None
                self._registry[registry + name] = (
                    pyctor.ref.RefImpl(registry=registry, name=name, strategy=remoteMessageStrategy),
                    self._remotes.get(registry, default_remote),
                )
                self._lock.release()
                return self._registry[registry + name][0]
            except trio.WouldBlock:
                return pyctor.ref.RefImpl(registry=registry, name=name, strategy=remoteMessageStrategy)

    def channel_from_ref(self, ref: pyctor.types.Ref[pyctor.types.T]) -> trio.abc.SendChannel[pyctor.types.T]:
        """
        Get the channel from a ref.
        If the ref is not available, then the fallback channel is used.
        If the fallback channel is not set, then a ValueError is raised.
        """
        if ref.url in self._registry:
            return self._registry[ref.url][1]
        elif self._fallback:
            return self._fallback
        raise ValueError(f"No channel for ref '{ref.url}'")

    def remotes(self) -> List[trio.abc.SendChannel]:
        """
        Get all remotes registered in this registry.
        """
        return [r for r in self._remotes.values()]
