import argparse
from logging import getLogger

import msgspec.msgpack
import trio

import pyctor
from pyctor import system
from pyctor.behaviors import Behaviors
from pyctor.multiprocess.messages import MultiProcessBase, ProcessMessage, SpawnRequest
from pyctor.types import Behavior, BehaviorSetup, Context, Ref

logger = getLogger(__name__)

class MultiProcessChildConnectionActor:
    """
    Actor on the side where we spawned a new process
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

    async def recv(self, self_ref: Ref[ProcessMessage]) -> None:
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

    async def setup(self, ctx: Context[ProcessMessage]) -> BehaviorSetup[ProcessMessage]:
        print("spawn subprocess")
        async with pyctor.open_nursery() as n:
            # start receive channel
            n._nursery.start_soon(self.recv, ctx.self)

            async def setup_handler(msg: ProcessMessage) -> Behavior[ProcessMessage]:
                print("send message")
                # Encode and write the response on the wire
                buffer = self._encoder.encode(msg)
                await self.send(buffer=buffer)
                
                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=MultiProcessBase)


def get_port() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Port for the multi processing", required=True)
    return int(parser.parse_args().port)


async def main() -> None:

    # Set 
    system.is_child = True;
    stream = await trio.open_tcp_stream("127.0.0.1", get_port())

    setup_behavior = Behaviors.setup(MultiProcessChildConnectionActor(stream=stream).setup)
    async with pyctor.open_nursery() as n:
        await n.spawn(setup_behavior)


if __name__ == "__main__":
    trio.run(main)
