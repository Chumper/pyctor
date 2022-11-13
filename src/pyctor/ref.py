
from pyctor.types import BehaviorProcessor, LifecycleSignal, Ref, ReplyProtocol, T, V


class LocalRef(Ref[T]):
    _impl: BehaviorProcessor[T]

    def __init__(self, behavior: BehaviorProcessor[T]) -> None:
        super().__init__()
        self._impl = behavior

    def send(self, msg: T) -> None:
        self._impl.handle(msg)

    async def ask(self, msg: ReplyProtocol[V]) -> V:  # type: ignore
        # TODO: Implement ad hoc child spawn and message reply
        pass

    def stop(self) -> None:
        self._impl.stop()

    def address(self) -> str:
        return "we don't know..."
