import logging
import platform
import sys
from dataclasses import dataclass
from functools import partial
from logging import getLogger
from typing import Any, Dict, List

import msgspec.msgpack
import trio

import pyctor
import pyctor.configuration
from pyctor.behaviors import Behaviors
from pyctor.multiprocess.connection import (
    MultiProcessServerConnectionReceiveActor,
    MultiProcessServerConnectionSendActor,
)
from pyctor.multiprocess.messages import (
    MessageCommand,
    MultiProcessMessage,
    SpawnCommand,
    StopCommand,
    decode_func,
    encode_func,
)
from pyctor.types import Behavior, BehaviorNursery, BehaviorSetup, Context, StoppedEvent

logger = getLogger(__name__)


@dataclass
class ProcessEntry:
    process: trio.Process
    is_connected: trio.Event
    send_ref: pyctor.types.Ref[MultiProcessMessage] | None = None
    receive_ref: pyctor.types.Ref[MultiProcessMessage] | None = None


class MultiProcessServerBehavior:
    """
    Q: What should happen if the multiprocess server actor crashes?
    A: Shut down the server and therefore terminate all actors on the system.
    """

    _max_processes: int
    """
    Max amount of processes
    """
    _spawn_counter: int = 0
    """
    Will be incremented each time a new behavior should be spawned.
    Indicates the process that should spawn the behavior.
    """
    _nursery: BehaviorNursery | None = None
    _children: Dict[int, ProcessEntry] = {}
    _context: pyctor.types.Context[SpawnCommand]

    def __init__(self, max_processes: int) -> None:
        self._max_processes = max_processes

    async def connection_handler(self, stream: trio.SocketStream) -> None:

        # spawn a new behavior for this stream
        # if this is called, a new process wants to participate in spawning behaviors
        # we will spawn a new ProcessBehavior that is responsible to:
        #   * send messages to the new process
        #   * spawn new behaviors on the new process
        #
        # when this method closes, then the stream will be closed...
        # so...
        # start a new nursery here for connection management?

        logger.debug("Child process connected")

        async with pyctor.open_nursery() as n:
            send_actor = MultiProcessServerConnectionSendActor.create(
                stream=stream,
                encoder=msgspec.msgpack.Encoder(
                    enc_hook=encode_func(pyctor.configuration._custom_encoder_function)
                ),
            )
            receive_actor = MultiProcessServerConnectionReceiveActor.create(
                stream=stream,
                decoder=msgspec.msgpack.Decoder(
                    SpawnCommand | StopCommand | StoppedEvent | MessageCommand,
                    dec_hook=decode_func(pyctor.configuration._custom_decoder_function),
                ),
                parent=self._context.self(),
            )

            send_ref = await n.spawn(send_actor)
            # register remote in registry
            registry: pyctor.types.Registry = pyctor.system.registry.get()
            # Hacky hack, need to do better
            await registry.register_remote(
                f"pyctor://{platform.node().lower()}/{self._spawn_counter}/", send_ref
            )
            receive_ref = await n.spawn(receive_actor)

            # TODO: watch the child for termination
            # if they die we terminate the system
            # because we can not guarantee the integrity
            # self._context.watch(send_ref, None)
            # self._context.watch(receive_ref, None)

            self._children[self._spawn_counter].receive_ref = receive_ref
            self._children[self._spawn_counter].send_ref = send_ref

            # notify that the children is available
            self._children[self._spawn_counter].is_connected.set()

    async def start_process(self, port: int) -> None:
        logger.debug(
            "Starting new trio child process with log level %s",
            str(logging.getLevelName(logging.getLogger().getEffectiveLevel())),
        )

        # spawn the process
        spawn_cmd = [
            sys.executable,
            "-m",
            "pyctor.multiprocess.child",
            "--port",
            str(port),
            "--log-level",
            str(logging.getLevelName(logging.getLogger().getEffectiveLevel())),
            "--index",
            str(self._spawn_counter),
        ]
        logger.debug("Running command: %s", spawn_cmd)
        process: trio.Process
        params = partial(trio.run_process, spawn_cmd)
        if self._nursery:
            process = await self._nursery._nursery.start(params)

            # wait until the process has connected back and there is a ref
            self._children[self._spawn_counter] = ProcessEntry(
                is_connected=trio.Event(), process=process
            )
            await self._children[self._spawn_counter].is_connected.wait()
            logger.debug("Child process connection established")

    async def setup(self, ctx: Context[SpawnCommand]) -> BehaviorSetup[SpawnCommand]:
        self._context = ctx

        logger.debug("Starting multiprocess server actor")

        async with pyctor.open_nursery() as n:
            self._nursery = n

            # start the server
            params = partial(
                trio.serve_tcp, self.connection_handler, 0, host="127.0.0.1"
            )
            listeners: List[trio.SocketListener] = await n._nursery.start(params)

            # get the port
            port = listeners[0].socket.getsockname()[1]
            logger.debug("Started multiprocess server on port %s", port)

            async def setup_handler(msg: SpawnCommand) -> Behavior[SpawnCommand]:
                # we only handle spawn requests, nothing else
                # type checking makes sure we only have that message here

                # determine the process index
                self._spawn_counter = (self._spawn_counter + 1) % self._max_processes

                # if the process children does not exist yet, we start it
                # with trio.fail_after(2):
                if self._spawn_counter not in self._children:
                    await self.start_process(port=port)

                process_entry = self._children[self._spawn_counter]
                # send same spawn message to child process
                if process_entry.send_ref:
                    process_entry.send_ref.send(msg=msg)

                return Behaviors.Same

            # return a type checked behavior
            yield Behaviors.receive(setup_handler, type_check=SpawnCommand)

            # cancel this scope
            n._nursery.cancel_scope.cancel()

    @staticmethod
    def create(max_processes: int):
        async def stop(e: Exception) -> pyctor.types.BehaviorSignal:
            logger.error(e)
            return Behaviors.Stop

        behavior = pyctor.behaviors.Behaviors.setup(
            MultiProcessServerBehavior(max_processes=max_processes).setup
        )
        return pyctor.behaviors.Behaviors.supervise(strategy=stop, behavior=behavior)
