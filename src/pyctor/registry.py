import platform
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import trio

import pyctor.ref
import pyctor.strategies
import pyctor.types

logger = getLogger(__name__)


class WatcherEntry(TypedDict):
    ref: pyctor.types.Ref[Any]
    msg: Any


localMessageStrategy: pyctor.types.MessageStrategy = pyctor.strategies.LocalMessageStrategy()
remoteMessageStrategy: pyctor.types.MessageStrategy = pyctor.strategies.RemoteMessageStrategy()


class RegistryImpl(pyctor.types.Registry):
    """
    A registry that contains the behavior channels for each address in this process.
    It is unique for each process and can be used in a thread safe way to find out
    which behaviors are placed on this process.
    """

    _url: str
    """
    The unique address of this registry
    """
    _lock: trio.Lock = trio.Lock()
    """
    A lock to guarantee safe access to the registry data
    """
    _index: int = 0
    """
    The index of this registry. 
    On a single node the main registry has the index 0.
    Each registry in a subprocess will have a higher index determined by the main process.
    With this index a registry can be uniquely identified.
    """
    _registry: Dict[str, Tuple[pyctor.types.Ref[Any], trio.abc.SendChannel]] = {}
    """
    Heart of the registry
    """
    _watchers: Dict[str, List[WatcherEntry]] = {}
    """
    Contains all behaviors in this process that want to watch other refs.
    It could be that a behavior wants to watch a ref in another process.
    It is important to know that this will only hold watchers in this process.
    Other registries could watch the same behavior just with different watchers. 
    """
    _remotes: Dict[str, trio.abc.SendChannel] = {}
    _default_remote: trio.abc.SendChannel = None

    def __init__(self) -> None:
        # determine registry name
        self._url = f"pyctor://{platform.node().lower()}/{self._index}/"

    def set_index(self, index: int) -> None:
        self._index = index
        self._url = f"pyctor://{platform.node().lower()}/{self._index}/"

    async def watch(self, ref: pyctor.types.Ref[pyctor.types.T], watcher: pyctor.types.Ref[pyctor.types.U], msg: pyctor.types.U) -> None:
        # add to watchers if available, send to ref immediately if not
        async with self._lock:
            if ref.url in self._watchers:
                # add to watcher
                self._watchers[ref.url].append(WatcherEntry(ref=watcher, msg=msg))
            else:
                # if the ref does not exist in this registry,
                # then we guarantee that it has been stopped already
                watcher.send(msg=msg)

    async def deregister(self, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        # remove from dict and call watchers
        async with self._lock:
            logger.info(f"Deregister ref: {ref.url}")
            if ref.url in self._registry:
                # available, so call watchers and remove from dict
                for entry in self._watchers[ref.url]:
                    entry["ref"].send(entry["msg"])
                # remove from dict
                del self._registry[ref.url]

    async def register(self, name: str, channel: trio.abc.SendChannel[pyctor.types.T]) -> pyctor.types.Ref[pyctor.types.T]:
        async with self._lock:
            if self._url + name in self._registry:
                raise ValueError(f"Ref {name} is already registered")
            self._registry[self._url + name] = (pyctor.ref.RefImpl(registry=self._url, name=name, strategy=localMessageStrategy), channel)
            self._watchers[self._url + name] = []
        return self._registry[self._url + name][0]

    async def register_remote(self, registry: str, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        async with self._lock:
            self._remotes[registry] = self.channel_from_ref(ref)

    def ref_from_raw(self, registry: str, name: str) -> pyctor.types.Ref[pyctor.types.T]:
        if registry == self._url and registry + name in self._registry:
            logger.debug("Returning LocalRef from wire: %s%s", registry, name)
            return self._registry[registry + name][0]
        elif registry != self._url and registry + name in self._registry:
            logger.debug("Returning RemoteRef from wire: %s%s", registry, name)
            return self._registry[registry + name][0]
        else:
            try:
                self._lock.acquire_nowait()
                self._registry[registry + name] = (
                    pyctor.ref.RefImpl(registry=registry, name=name, strategy=remoteMessageStrategy),
                    self._remotes.get(registry, self._default_remote),
                )
                self._lock.release()
                return self._registry[registry + name][0]
            except trio.WouldBlock:
                return pyctor.ref.RefImpl(registry=registry, name=name, strategy=remoteMessageStrategy)

    def channel_from_ref(self, ref: pyctor.types.Ref[pyctor.types.T]) -> trio.abc.SendChannel[pyctor.types.T]:
        if ref.url in self._registry:
            return self._registry[ref.url][1]
        raise ValueError(f"No Behavior with ref '{ref.url}'")

    def register_default_remote(self, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        self._default_remote = self.channel_from_ref(ref)
