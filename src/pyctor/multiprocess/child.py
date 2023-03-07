import argparse
import logging
import os
import sys
from logging import getLogger
from typing import Any, Callable, Tuple, Type

import cloudpickle  # type: ignore
import msgspec.msgpack
import tricycle
import trio

import pyctor
import pyctor.configuration
import pyctor.registry
from pyctor import system
from pyctor.behaviors import Behaviors
from pyctor.configuration import set_custom_decoder_function, set_custom_encoder_function
from pyctor.multiprocess.messages import (
    MessageCommand,
    MultiProcessMessage,
    SpawnCommand,
    StartedEvent,
    StopCommand,
    StoppedEvent,
    decode_func,
    get_type,
)
from pyctor.types import Behavior, BehaviorGeneratorFunction, BehaviorSetup, Context, Ref

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
        self, _: Context[MultiProcessMessage]
    ) -> BehaviorSetup[MultiProcessMessage]:

        logger.info("MultiProcess Child Send Actor started")

        async def setup_handler(
            msg: MultiProcessMessage,
        ) -> Behavior[MultiProcessMessage]:
            # any message we get we send on the wire...
            print(f"Child-Send: type: {type(msg)} - content: {msg}")
            match msg:
                case SpawnCommand() | StopCommand() | MessageCommand() | StartedEvent() | StoppedEvent():
                    buffer = self._encoder.encode(msg)
                    await self.send(buffer=buffer)
                case _:
                    print(f"Child-Send: ignore type: {type(msg)} - content: {msg}")
                    return Behaviors.Ignore
            return Behaviors.Same

        # return a type checked behavior
        yield Behaviors.receive(setup_handler)

    @staticmethod
    def create(
        stream: trio.SocketStream, encoder: msgspec.msgpack.Encoder
    ) -> BehaviorGeneratorFunction[MultiProcessMessage]:
        return Behaviors.setup(
            MultiProcessChildConnectionSendActor(stream=stream, encoder=encoder).setup
        )


class MultiProcessChildConnectionReceiveActor:
    """
    Actor on the side where we spawned a new process.
    Responsible to receive messages from the wire and act on them
    """

    _stream: tricycle.BufferedReceiveStream
    _decoder: msgspec.msgpack.Decoder
    _remote: Ref[MultiProcessMessage]

    def __init__(
        self,
        stream: trio.SocketStream,
        decoder: msgspec.msgpack.Decoder,
        remote: Ref[MultiProcessMessage],
    ) -> None:
        self._stream = tricycle.BufferedReceiveStream(transport_stream=stream)
        self._decoder = decoder
        self._remote = remote

    async def recv(self, self_ref: Ref[MultiProcessMessage]) -> None:
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
        self, ctx: Context[MultiProcessMessage]
    ) -> BehaviorSetup[MultiProcessMessage]:

        logger.info("MultiProcess Child Receive Actor started")

        async with pyctor.open_nursery() as n:
            # start receive channel
            n._nursery.start_soon(self.recv, ctx.self())

            async def setup_handler(
                msg: MultiProcessMessage,
            ) -> Behavior[MultiProcessMessage]:
                match msg:
                    case SpawnCommand(reply_to, behavior, name):
                        print(f"{os.getpid()}: spawn behavior")
                        decoded_behavior = cloudpickle.loads(behavior)
                        spawned_ref = await n.spawn(
                            behavior=decoded_behavior, name=name
                        )
                        # send the ref back to the orginial spawner
                        reply_to.send(spawned_ref)
                        # force order, not sure if that is needed
                        await trio.sleep(0)
                        # send an even to the master that we spawned a child
                        self._remote.send(StartedEvent(spawned_ref))
                    case StopCommand():
                        print(f" {os.getpid()}: stop ref")
                    case MessageCommand():
                        print(f" {os.getpid()}: send behavior")
                        type = get_type(msg.type)
                        new_msg = msgspec.msgpack.decode(msg.msg, dec_hook=decode_func(pyctor.configuration._custom_decoder_function), type=type)
                        msg.ref.send(msg=new_msg)
                    case StartedEvent():
                        print(f" {os.getpid()}: behavior started")
                    case StoppedEvent():
                        print(f" {os.getpid()}: behavior stopped")
                    case _:
                        return Behaviors.Ignore
                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=MultiProcessMessage)

            # stop the stream
            logger.info("Closing stream!!!")
            await self._stream.aclose()

    @staticmethod
    def create(
        stream: trio.SocketStream,
        decoder: msgspec.msgpack.Decoder,
        remote: Ref[MultiProcessMessage],
    ) -> BehaviorGeneratorFunction[MultiProcessMessage]:
        return Behaviors.setup(
            MultiProcessChildConnectionReceiveActor(
                stream=stream, decoder=decoder, remote=remote
            ).setup
        )


async def get_callable(stream: trio.SocketStream) -> Any:
    try:
        s = tricycle.BufferedReceiveStream(transport_stream=stream)
        prefix = await s.receive_exactly(4)
        n = int.from_bytes(prefix, "big")
        logger.info("MultiProcess child will receive callable with %s bytes", str(n))
        data = await s.receive_exactly(n)

        return cloudpickle.loads(data)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


def get_arg() -> Tuple[int, int, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", help="Port for the multi processing", required=True
    )
    parser.add_argument(
        "-i", "--index", help="Index of this multi processing process", required=True
    )
    parser.add_argument("-l", "--log-level", help="Log level", required=True)
    args = parser.parse_args()
    return int(args.port), int(args.index), str(args.log_level)


async def main() -> None:
    port, registry_index, log_level = get_arg()

    reg: pyctor.types.Registry = pyctor.system.registry.get()
    reg.set_index(registry_index)

    # set log level
    logging.basicConfig(level=log_level)

    logger.info("MultiProcess Child Process starting")

    # Set
    system.is_child = True
    stream = await trio.open_tcp_stream("127.0.0.1", port=port)

    logger.info("MultiProcess Child connected to port %s", str(port))

    # get encoding and decoding functions
    encoder: Callable[[Any], Any] = await get_callable(stream=stream)
    decoder: Callable[[Type, Any], Any] = await get_callable(stream=stream)

    set_custom_encoder_function(encoder)
    set_custom_decoder_function(decoder)

    logger.info("MultiProcess Child received encoder and decoder")

    # as we are already a child process we should not start a multi process nursery
    # instead we will be a good child and only spawn new behaviors in our own process. 
    async with pyctor.open_nursery() as n:
        # start two behaviors, one for receiving, one for sending
        send_actor = MultiProcessChildConnectionSendActor.create(
            stream=stream, encoder=msgspec.msgpack.Encoder(enc_hook=encoder)
        )
        send_ref = await n.spawn(send_actor)

        receive_actor = MultiProcessChildConnectionReceiveActor.create(
            stream=stream,
            decoder=msgspec.msgpack.Decoder(
                SpawnCommand
                | StopCommand
                | StartedEvent
                | StoppedEvent
                | MessageCommand,
                dec_hook=decoder,
            ),
            remote=send_ref,
        )

        # register as default remote channel so that refs from the wire have a channel associated
        registry: pyctor.types.Registry = pyctor.system.registry.get()
        registry.register_default_remote(send_ref)
        await n.spawn(receive_actor)

    print("Closing...")


if __name__ == "__main__":
    trio.run(main)
