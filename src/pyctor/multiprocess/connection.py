import sys
from functools import partial
from logging import getLogger

import msgspec.msgpack
import trio

from pyctor.behaviors import Behaviors
from pyctor.multiprocess.messages import MultiProcessBase, ProcessMessage, SpawnRequest
from pyctor.types import Behavior, BehaviorSetup, Context, Ref

logger = getLogger(__name__)

class MultiProcessServerConnectionActor:
    """
    Actor on the side where the main process is running
    """
    
    _stream: trio.SocketStream
    _decoder: msgspec.msgpack.Decoder
    _encoder: msgspec.msgpack.Encoder
    _stopped: trio.Event = trio.Event()

    def __init__(self, stream: trio.SocketStream) -> None:
        self._stream = stream
        # match the specified types, a nice error will be raised.
        self._decoder = msgspec.msgpack.Decoder(MultiProcessBase)
        self._enoder = msgspec.msgpack.Encoder()

    async def send(self, buffer: bytes) -> None:
        prefix = len(buffer).to_bytes(4, "big")
        # Write the prefix and buffer to the stream.
        await self._stream.send_all(prefix)
        await self._stream.send_all(buffer)

    async def recv(self, self_ref: Ref[MultiProcessBase]) -> None:
        while not self._stopped.is_set():
            try:
                prefix = await self._stream.receive_some(4)
                n = int.from_bytes(prefix, "big")
                data = await self._stream.receive_some(n)
                # decode
                req: MultiProcessBase = self._decoder.decode(data)
                # send to self ref
                self_ref.send(req)

            except Exception as e:
                # stop the stream
                self._stopped.set()
                await self._stream.aclose()
                await self_ref.stop()
                logger.exception(e)

    async def setup(self, ctx: Context[SpawnRequest]) -> BehaviorSetup[SpawnRequest]:
        print("spawn subprocess")
        async with trio.open_nursery() as n:
            # start receive channel
            n.start_soon(self.recv, ctx.self)

            async def setup_handler(msg: MultiProcessBase) -> Behavior[MultiProcessBase]:
                match msg:
                    case SpawnRequest(reply_to, behavior, name):
                        print("spawn behavior")
                    case ProcessMessage():
                        print("send message")
                        # Encode and write the response
                        buffer = self._encoder.encode(msg)
                        await self.send(buffer=buffer)
                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=MultiProcessBase)
