from logging import getLogger

import msgspec
import trio

import pyctor
from pyctor.multiprocess.messages import (
    MessageCommand,
    MultiProcessMessage,
    SpawnCommand,
    StopCommand,
)
from pyctor.types import StoppedEvent

logger = getLogger(__name__)


class MultiProcessChildConnectionSendActor:
    """
    Actor on the side where we spawned a new process.
    Responsible to send messages on the stream to the parent process
    """

    _stream: trio.SocketStream
    _encoder: msgspec.msgpack.Encoder

    def __init__(
        self, stream: trio.SocketStream, encoder: msgspec.msgpack.Encoder
    ) -> None:
        self._stream = stream
        self._encoder = encoder

    async def send(self, buffer: bytes) -> None:
        prefix = len(buffer).to_bytes(4, "big")
        # Write the prefix and buffer to the stream.
        logger.debug(f"Child: Sending %s on the wire", len(buffer))
        await self._stream.send_all(prefix)
        await self._stream.send_all(buffer)

    async def setup(
        self, _: pyctor.types.Context[MultiProcessMessage]
    ) -> pyctor.types.BehaviorSetup[MultiProcessMessage]:

        logger.info("MultiProcess Child Send Actor started")

        async def setup_handler(
            msg: MultiProcessMessage,
        ) -> pyctor.types.Behavior[MultiProcessMessage]:
            # any message we get we send on the wire...
            print(f"Child-Send: type: {type(msg)} - content: {msg}")
            match msg:
                case SpawnCommand() | StopCommand() | MessageCommand() | StoppedEvent():
                    buffer = self._encoder.encode(msg)
                    await self.send(buffer=buffer)
                case _:
                    print(f"Child-Send: ignore type: {type(msg)} - content: {msg}")
                    return pyctor.behaviors.Behaviors.Ignore
            return pyctor.behaviors.Behaviors.Same

        # return a type checked behavior
        yield pyctor.behaviors.Behaviors.receive(setup_handler)

    @staticmethod
    def create(
        stream: trio.SocketStream, encoder: msgspec.msgpack.Encoder
    ) -> pyctor.types.BehaviorGeneratorFunction[MultiProcessMessage]:
        return pyctor.behaviors.Behaviors.setup(
            MultiProcessChildConnectionSendActor(stream=stream, encoder=encoder).setup
        )
