from logging import getLogger

import cloudpickle  # type: ignore
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


class MultiProcessServerConnectionSendActor:
    """
    Actor on the side where the main process is running.
    Responsible to send messages to the child process.
    """

    _stream: trio.SocketStream
    _encoder: msgspec.msgpack.Encoder
    _context: pyctor.types.Context[MultiProcessMessage]

    def __init__(
        self, stream: trio.SocketStream, encoder: msgspec.msgpack.Encoder
    ) -> None:
        self._stream = stream
        self._encoder = encoder

    async def send(self, buffer: bytes) -> None:
        prefix = len(buffer).to_bytes(4, "big")
        # Write the prefix and buffer to the stream.
        logger.debug("Sending 4 + %s bytes on the wire", str(len(buffer)))
        try:
            await self._stream.send_all(prefix)
            await self._stream.send_all(buffer)
        except Exception as e:
            logger.exception(e)
            self._context.self().stop()

    async def setup(
        self, ctx: pyctor.types.Context[MultiProcessMessage]
    ) -> pyctor.types.BehaviorSetup[MultiProcessMessage]:
        self._context = ctx

        logger.debug("MultiProcess Server Send Actor started")

        # first send encoder and decoder to child process
        await self.send(
            cloudpickle.dumps(
                pyctor.multiprocess.messages.encode_func(
                    pyctor.configuration._custom_encoder_function
                )
            )
        )
        await self.send(
            cloudpickle.dumps(
                pyctor.multiprocess.messages.decode_func(
                    pyctor.configuration._custom_decoder_function
                )
            )
        )

        logger.debug("Sent encoder and decoder to child process")

        async def setup_handler(
            msg: MultiProcessMessage,
        ) -> pyctor.types.Behavior[MultiProcessMessage]:
            match msg:
                case SpawnCommand() | MessageCommand() | StopCommand():
                    logger.debug("Handling message of type %s", type(msg))
                    # encode and write to wire
                    buffer = self._encoder.encode(msg)
                    await self.send(buffer=buffer)
                case StoppedEvent():
                    # do not send if this subprocess registry is the origin of the message
                    logger.debug("Handling message of type %s", type(msg))
                    # encode and write to wire
                    buffer = self._encoder.encode(msg)
                    await self.send(buffer=buffer)
                case _:
                    logger.warning(f"Ignoring message: {type(msg)} -> {msg}")
                    return pyctor.behaviors.Behaviors.Ignore

            return pyctor.behaviors.Behaviors.Same

        # return a type checked behavior
        yield pyctor.behaviors.Behaviors.receive(setup_handler)

    @staticmethod
    def create(
        stream: trio.SocketStream, encoder: msgspec.msgpack.Encoder
    ) -> pyctor.types.BehaviorGeneratorFunction[MultiProcessMessage]:
        async def ignore(e: Exception) -> pyctor.types.BehaviorSignal:
            logger.error(e)
            return pyctor.behaviors.Behaviors.Stop

        setup = pyctor.behaviors.Behaviors.setup(
            MultiProcessServerConnectionSendActor(stream=stream, encoder=encoder).setup
        )
        return pyctor.behaviors.Behaviors.supervise(strategy=ignore, behavior=setup)
