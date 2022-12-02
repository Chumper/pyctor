from typing import List

import trio
import trio.abc

import pyctor.types


class StashImpl(pyctor.types.Stash[pyctor.types.T]):
    _send: trio.abc.SendChannel
    _receive: trio.abc.ReceiveChannel

    def __init__(self, amount: int) -> None:
        super().__init__()
        self._send, self._receive = trio.open_memory_channel(amount)

    async def stash(self, msg: pyctor.types.T) -> None:
        await self._send.send(msg)

    async def unstash(self, amount: int) -> List[pyctor.types.T]:
        messages: List[pyctor.types.T] = []
        for i in range(amount):
            messages.append(await self._receive.receive())
        return messages

    async def close(self) -> None:
        await self._send.aclose()
        await self._receive.aclose()
