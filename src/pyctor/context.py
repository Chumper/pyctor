import pyctor.types

class ContextImpl(pyctor.types.Context[pyctor.types.T]):
    _ref: pyctor.types.Ref[pyctor.types.T]

    def __init__(self, ref: pyctor.types.Ref[pyctor.types.T]) -> None:
        super().__init__()
        self._ref = ref
