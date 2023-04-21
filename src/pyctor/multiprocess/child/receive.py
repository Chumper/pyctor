import os
from logging import getLogger

import cloudpickle  # type: ignore
import msgspec
import tricycle
import trio

import pyctor
from pyctor.multiprocess.messages import (
    MessageCommand,
    MultiProcessMessage,
    SpawnCommand,
    StopCommand,
    decode_func,
    get_type,
)
from pyctor.types import StoppedEvent

logger = getLogger(__name__)


class MultiProcessChildConnectionReceiveBehavior:
    """
    Actor on the side where we spawned a new process.
    Responsible to receive messages from the wire and act on them
    """

    _stream: tricycle.BufferedReceiveStream
    _decoder: msgspec.msgpack.Decoder
    _registry: pyctor.types.Registry

    def __init__(
        self,
        stream: tricycle.BufferedReceiveStream,
        decoder: msgspec.msgpack.Decoder,
        registry: pyctor.types.Registry,
    ) -> None:
        self._stream = stream
        self._decoder = decoder
        self._registry = registry

    async def recv(self, self_ref: pyctor.types.Ref[MultiProcessMessage]) -> None:
        while True:
            try:
                prefix = await self._stream.receive_exactly(4)
                n = int.from_bytes(prefix, "big")
                data = await self._stream.receive_exactly(n)
                # decode
                req: MultiProcessMessage = self._decoder.decode(data)
                # send to self ref
                self_ref.send(req)

            except Exception as e:
                logger.error(e)
                self_ref.stop()
                break

    async def setup(
        self, ctx: pyctor.types.Context[MultiProcessMessage]
    ) -> pyctor.types.BehaviorSetup[MultiProcessMessage]:

        logger.info("MultiProcess Child Receive Actor started")

        async with pyctor.open_nursery() as n:
            # start receive channel
            n._nursery.start_soon(self.recv, ctx.self())

            async def setup_handler(
                msg: MultiProcessMessage,
            ) -> pyctor.types.Behavior[MultiProcessMessage]:
                match msg:
                    case SpawnCommand(reply_to, behavior, options):
                        print(f"{os.getpid()}: spawn behavior")
                        decoded_behavior = cloudpickle.loads(behavior)
                        spawned_ref = await n.spawn(
                            behavior=decoded_behavior, options=options
                        )
                        # send the ref back to the orginial spawner
                        reply_to.send(spawned_ref)
                        # force order, not sure if that is needed
                        await trio.sleep(0)
                    case StopCommand():
                        print(f"{os.getpid()}: stop ref")
                        # stop the ref
                        msg.ref.stop()
                    case MessageCommand():
                        print(f"{os.getpid()}: send behavior")
                        type = get_type(msg.type)
                        new_msg = msgspec.msgpack.decode(
                            msg.msg,
                            dec_hook=decode_func(
                                pyctor.configuration._custom_decoder_function
                            ),
                            type=type,
                        )
                        msg.ref.send(msg=new_msg)
                    case StoppedEvent():
                        print(f"{os.getpid()}: behavior stopped")
                        # send to registry
                        await self._registry.deregister(msg.ref)
                    case _:
                        return pyctor.behaviors.Behaviors.Ignore
                # return the same behavior as long as we have children
                # if we have no children, then we should stop ourselves.
                # When the behavior is started we will get an initial spawn message
                # so it is guaranteed that the first message will spawn a child.
                return (
                    pyctor.behaviors.Behaviors.Same
                    if n.children
                    else pyctor.behaviors.Behaviors.Stop
                )

            # return a type checked behavior
            yield pyctor.behaviors.Behaviors.receive(
                setup_handler, type_check=MultiProcessMessage
            )

            # stop the stream
            logger.info("Closing stream!!!")
            await self._stream.aclose()

    @staticmethod
    def create(
        stream: tricycle.BufferedReceiveStream,
        decoder: msgspec.msgpack.Decoder,
        registry: pyctor.types.Registry,
    ) -> pyctor.types.BehaviorGeneratorFunction[MultiProcessMessage]:
        return pyctor.behaviors.Behaviors.setup(
            MultiProcessChildConnectionReceiveBehavior(
                stream=stream, decoder=decoder, registry=registry
            ).setup
        )
