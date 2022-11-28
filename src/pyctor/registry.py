import os
import platform
import threading
from contextlib import _AsyncGeneratorContextManager
from typing import Callable, Dict, overload

import trio

import pyctor.ref
import pyctor.types


class BehaviorRegistry:
    """
    A registry that contains the behavior channels for each address in this process.
    It is unique for each process and can be used in a thread safe way to find out
    which behaviors are placed on this process.
    """

    _registry: Dict[str, trio.abc.SendChannel[pyctor.types.T]] = {}
    _lock: threading.Lock = threading.Lock()
    _url_prefix: str

    def __init__(self) -> None:
        # create registry name
        self._url_prefix = f"pyctor://{platform.node()}/{os.getpid()}/"

    def register(self, name: str, channel: trio.abc.SendChannel[pyctor.types.T]) -> pyctor.types.Ref[pyctor.types.T]:
        with self._lock:
            if name in self._registry:
                raise ValueError(f"Ref {name} is already registered")
            self._registry[self._url_prefix + name] = channel
        return pyctor.ref.LocalRef(self._url_prefix + name)

    def get(self, ref: pyctor.types.Ref[pyctor.types.T]) -> trio.abc.SendChannel[pyctor.types.T]:
        if ref.url in self._registry:
            return self._registry[ref.url]
        raise ValueError(f"No Behavior with ref '{ref}'")

    def get_name(self, name: str) -> trio.abc.SendChannel[pyctor.types.T]:
        if f"{self._url_prefix}{name}" in self._registry:
            return self._registry[name]
        raise ValueError(f"No Behavior with name '{name}'")
