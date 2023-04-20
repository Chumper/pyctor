from logging import getLogger

import msgspec
import tricycle
import trio

import pyctor
from pyctor.multiprocess.messages import MessageCommand, MultiProcessMessage, SpawnCommand, StopCommand, decode_func, get_type
from pyctor.types import StoppedEvent

logger = getLogger(__name__)


class MultiProcessServerConnectionReceiveActor:
    """
    Actor on the side where the main process is running.
    Responsible to receive the the events from the child process
    """

    _stream: tricycle.BufferedReceiveStream
    _decoder: msgspec.msgpack.Decoder
    _parent: pyctor.types.Ref[SpawnCommand]

    def __init__(
        self,
        stream: trio.SocketStream,
        decoder: msgspec.msgpack.Decoder,
        parent: pyctor.types.Ref[SpawnCommand],
    ) -> None:
        self._stream = tricycle.BufferedReceiveStream(transport_stream=stream)
        self._decoder = decoder
        self._parent = parent

    async def recv(self, self_ref: pyctor.types.Ref[MultiProcessMessage]) -> None:
        run = True
        while run:
            try:
                prefix = await self._stream.receive_exactly(4)
                n = int.from_bytes(prefix, "big")

                logger.debug("Server: Receiving %s bytes from the wire", str(n))

                data = await self._stream.receive_exactly(n)
                # decode
                req: MultiProcessMessage = self._decoder.decode(data)
                # send to self ref
                self_ref.send(req)

            except Exception as e:
                run = False
                logger.exception(e)
                self_ref.stop()
                break

    async def setup(self, ctx: pyctor.types.Context[MultiProcessMessage]) -> pyctor.types.BehaviorSetup[MultiProcessMessage]:
        logger.debug("MultiProcess Server Receive Actor started")
        async with trio.open_nursery() as n:
            # start receive channel
            n.start_soon(self.recv, ctx.self())

            async def setup_handler(
                msg: MultiProcessMessage,
            ) -> pyctor.types.Behavior[MultiProcessMessage]:
                match msg:
                    case SpawnCommand():
                        logger.debug("spawning ref on some node")
                        self._parent.send(msg)
                    case StopCommand():
                        # TODO: Send to all child connections and same registry
                        logger.info("stop ref")
                        msg.ref.stop()
                    case MessageCommand():
                        logger.info("send message to ref")
                        # decode message first
                        type = get_type(msg.type)
                        new_msg = msgspec.msgpack.decode(
                            msg.msg,
                            dec_hook=decode_func(pyctor.configuration._custom_decoder_function),
                            type=type,
                        )
                        msg.ref.send(msg=new_msg)
                    case StoppedEvent():
                        # We got a stopped event, we only get this when the sub process has a stopped behavior
                        # In that case we will send this message to all remotes in the registry
                        registry: pyctor.types.Registry = pyctor.system.registry.get()
                        for r in registry.remotes():
                            await r.send(msg)
                        logger.info("ref stopped on child")
                    case _:
                        logger.warning(f"Ignoring message: {type(msg)} -> {msg}")
                        return pyctor.behaviors.Behaviors.Ignore

                return pyctor.behaviors.Behaviors.Same

            # return a type checked behavior
            yield pyctor.behaviors.Behaviors.receive(setup_handler)

            # close the stream
            logger.info("Closing stream!!!")
            await self._stream.aclose()

    @staticmethod
    def create(
        stream: trio.SocketStream,
        decoder: msgspec.msgpack.Decoder,
        parent: pyctor.types.Ref[SpawnCommand],
    ) -> pyctor.types.BehaviorGeneratorFunction[MultiProcessMessage]:
        async def ignore(e: Exception) -> pyctor.types.BehaviorSignal:
            logger.error(e)
            return pyctor.behaviors.Behaviors.Stop

        setup = pyctor.behaviors.Behaviors.setup(MultiProcessServerConnectionReceiveActor(stream=stream, decoder=decoder, parent=parent).setup)
        return pyctor.behaviors.Behaviors.supervise(strategy=ignore, behavior=setup)
