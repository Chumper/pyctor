from pyctor.registry import RegistryImpl
import pyctor.types


class ContextImpl(pyctor.types.Context[pyctor.types.T]):
    _ref: pyctor.types.Ref[pyctor.types.T]

    def __init__(self, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        super().__init__()
        self._ref = ref

    def self(self) -> pyctor.types.Ref[pyctor.types.T]:
        return self._ref

    async def watch(self, ref: pyctor.types.Ref[pyctor.types.U], msg: pyctor.types.T) -> None:
        registry: pyctor.types.Registry = pyctor.system.registry.get()
        await registry.watch(ref=ref, watcher=self._ref, msg=msg)
