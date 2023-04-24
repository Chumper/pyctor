import os
from logging import getLogger
from typing import Any, TypeAlias, Union

import cloudpickle  # type: ignore
import msgspec
import tricycle
import trio

import pyctor
from pyctor.multiprocess.child.uncle import UncleBehavior
from pyctor.multiprocess.messages import (
    MessageCommand,
    MultiProcessMessage,
    SpawnCommand,
    StopCommand,
    decode_func,
    str_to_type,
)
from pyctor.types import StoppedEvent

logger = getLogger(__name__)


class StopSubProcess(msgspec.Struct):
    """
    Simple message to stop the subprocess
    """

    pass


Messages: TypeAlias = Union[
    SpawnCommand, StopCommand, MessageCommand, StoppedEvent, StopSubProcess
]


class MultiProcessChildConnectionReceiveBehavior:
    """
    Actor on the side where we spawned a new process.
    Responsible to receive messages from the wire and act on them.
    The behavior works on the following message types:
    - SpawnCommand: spawns a new behavior as a childand sends the ref back to the logical parent
    - StopCommand: stops the given ref if it is part of the current process, otherwise it will send a stop command to the ref. Logically the ref to be stopped will always be a part of the current process.
    - MessageCommand: sends a message to the given ref, if the ref is not part of the current process it will send a remote message command to the ref.
    - StoppedEvent: will tell the registry that the given ref has stopped, watchers of that ref will be notified.
    """

    _stream: tricycle.BufferedReceiveStream
    _decoder: msgspec.msgpack.Decoder
    _registry: pyctor.types.Registry
    _children: list[pyctor.types.Ref[Any]] = []

    def __init__(
        self,
        stream: tricycle.BufferedReceiveStream,
        decoder: msgspec.msgpack.Decoder,
        registry: pyctor.types.Registry,
    ) -> None:
        self._stream = stream
        self._decoder = decoder
        self._registry = registry

    async def recv(
        self, self_ref: pyctor.types.Ref[Union[MultiProcessMessage, StoppedEvent]]
    ) -> None:
        while True:
            try:
                prefix = await self._stream.receive_exactly(4)
                n = int.from_bytes(prefix, "big")
                data = await self._stream.receive_exactly(n)
                # decode
                req: MultiProcessMessage | StoppedEvent = self._decoder.decode(data)
                # send to self ref
                self_ref.send(req)

            except Exception as e:
                logger.error(e)
                self_ref.stop()
                break

    async def setup(
        self, ctx: pyctor.types.Context[Messages]
    ) -> pyctor.types.BehaviorSetup[Messages]:

        logger.info("MultiProcess Child Receive Actor started")

        async with pyctor.open_nursery() as n:
            # start receive channel
            n._nursery.start_soon(self.recv, ctx.self())

            # spawn the uncle behavior that will handle all SpawnCommands
            uncle_ref = await n.spawn(
                UncleBehavior.create(), options={"name": f"{os.getpid()}-uncle"}
            )
            # watch the uncle, if the uncle stops we should stop as well
            await ctx.watch(uncle_ref, StopSubProcess())

            async def setup_handler(
                msg: Messages,
            ) -> pyctor.types.Behavior[Messages]:
                match msg:
                    case SpawnCommand(reply_to, behavior, options):
                        print(f"{os.getpid()}: spawn behavior")
                        # forward to the uncle
                        uncle_ref.send(msg=msg)
                    case StopCommand():
                        print(f"{os.getpid()}: stop ref")
                        # stop the ref
                        msg.ref.stop()
                    case MessageCommand():
                        print(f"{os.getpid()}: send behavior")
                        type = str_to_type(msg.type)
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
                    case StopSubProcess():
                        # stop the subprocess
                        print(f"{os.getpid()}: stop subprocess")
                        return pyctor.behaviors.Behaviors.Stop
                    case _:
                        return pyctor.behaviors.Behaviors.Ignore

                return pyctor.behaviors.Behaviors.Same

            # return a type checked behavior
            yield pyctor.behaviors.Behaviors.receive(
                setup_handler, type_check=Messages  # type: ignore
            )

            # stop the stream
            logger.info("Closing stream!!!")
            await self._stream.aclose()

    @staticmethod
    def create(
        stream: tricycle.BufferedReceiveStream,
        decoder: msgspec.msgpack.Decoder,
        registry: pyctor.types.Registry,
    ) -> pyctor.types.BehaviorGeneratorFunction[Messages]:
        # create the behavior
        setup_behavior = pyctor.behaviors.Behaviors.setup(
            MultiProcessChildConnectionReceiveBehavior(
                stream=stream, decoder=decoder, registry=registry
            ).setup
        )

        # define a supervisor method that will stop the behavior on any exception
        async def supervisor(exception: Exception) -> pyctor.types.BehaviorSignal:
            print(f"Supervisor: {exception}")
            return pyctor.behaviors.Behaviors.Stop

        # wrap the behavior in a supervisor
        return pyctor.behaviors.Behaviors.supervise(
            behavior=setup_behavior, strategy=supervisor
        )
