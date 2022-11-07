
from pyctor.types import T, V, BehaviorProcessor, Ref, ReplyProtocol


class LocalRef(Ref[T]):
    _impl: BehaviorProcessor[T]

    def __init__(self, behavior: BehaviorProcessor[T]) -> None:
        super().__init__()
        self._impl = behavior

    async def send(self, msg: T) -> None:
        await self._impl.handle(msg)

    async def ask(self, msg: ReplyProtocol[V]) -> V:  # type: ignore
        # TODO: Implement ad hoc child spawn and message reply
        pass
