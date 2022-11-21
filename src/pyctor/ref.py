from typing import Callable, Type, cast

import pyctor.behavior
import pyctor.signals
import pyctor.system
import pyctor.types


class LocalRef(pyctor.types.Ref[pyctor.types.T]):
    _impl: pyctor.types.BehaviorProcessor[pyctor.types.T]

    def __init__(
        self, behavior: pyctor.types.BehaviorProcessor[pyctor.types.T]
    ) -> None:
        super().__init__()
        self._impl = behavior

    async def send(self, msg: pyctor.types.T) -> None:
        await self._impl.handle(msg)

    def send_nowait(self, msg: pyctor.types.T) -> None:
        self._impl.handle_nowait(msg)

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

            reply_ref = await n.spawn(
                pyctor.behavior.BehaviorHandlerImpl(behavior=receive_behavior)
            )
            await self.send(f(reply_ref))
        return response

    async def stop(self) -> None:
        await self._impl.stop()

    def address(self) -> str:
        return self._impl._name

    def unsafe_cast(
        self, clazz: Type[pyctor.types.U]
    ) -> pyctor.types.Ref[pyctor.types.U]:
        return cast(pyctor.types.Ref[pyctor.types.U], self)
