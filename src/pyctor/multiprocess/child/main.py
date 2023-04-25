import argparse
import logging
import platform
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
from pyctor.configuration import set_custom_decoder_function, set_custom_encoder_function
from pyctor.dispatch.single_process import spawn_system_behavior
from pyctor.multiprocess.child.receive import MultiProcessChildConnectionReceiveBehavior
from pyctor.multiprocess.child.send import MultiProcessChildConnectionSendActor
from pyctor.multiprocess.messages import MessageCommand, SpawnCommand, StopCommand
from pyctor.multiprocess.mp_fixup_main import _fixup_main_from_name, _fixup_main_from_path, _mp_figure_out_main
from pyctor.types import StoppedEvent

logger = getLogger(__name__)


async def get_callable(stream: tricycle.BufferedReceiveStream) -> Any:
    try:
        prefix = await stream.receive_exactly(4)
        n = int.from_bytes(prefix, "big")
        logger.info("MultiProcess child will receive callable with %s bytes", str(n))
        data = await stream.receive_exactly(n)

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

    # set log level
    logging.basicConfig(level=log_level)

    logger.debug("connecting to parent port=%s", str(port))

    # setup the main module
    main_data = _mp_figure_out_main()
    print(main_data)
    if 'init_main_from_name' in main_data:
        _fixup_main_from_name(main_data['init_main_from_name'])
    elif 'init_main_from_path' in main_data:
        _fixup_main_from_path(main_data['init_main_from_path'])

    # Set
    stream = await trio.open_tcp_stream("127.0.0.1", port=port)

    logger.debug("connected to parent port=%s", str(port))

    # get encoding and decoding functions
    s = tricycle.BufferedReceiveStream(transport_stream=stream)
    encoder: Callable[[Any], Any] = await get_callable(stream=s)
    decoder: Callable[[Type, Any], Any] = await get_callable(stream=s)

    set_custom_encoder_function(encoder)
    set_custom_decoder_function(decoder)

    logger.debug("encoder and decoder received")

    # create the send actor, which will send messages to the parent process
    send_actor = MultiProcessChildConnectionSendActor.create(
        stream=stream, encoder=msgspec.msgpack.Encoder(enc_hook=encoder)
    )

    # start a trio nursery
    async with trio.open_nursery() as n:
        # spawn the system ref for the send behavior
        ref = await spawn_system_behavior(
            behavior=send_actor,
            nursery=n,
            options={"name": f"child/{registry_index}/send"},
        )

        # create a new registry
        reg = pyctor.registry.RegistryImpl(
            name=f"{platform.node().lower()}/{registry_index}",
            fallback=ref._channel,
        )
        # set the registry as the default registry
        pyctor.system.registry.set(reg)

        # create the receive actor, which will receive messages from the parent process
        receive_actor = MultiProcessChildConnectionReceiveBehavior.create(
            stream=s,
            decoder=msgspec.msgpack.Decoder(
                SpawnCommand | StopCommand | StoppedEvent | MessageCommand,
                dec_hook=decoder,
            ),
            registry=reg,
        )
        # as we are already a child process we should not start a multi process nursery
        # instead we will be a good child and only spawn new behaviors in our own process.
        async with pyctor.open_nursery() as bn:
            # spawn the receive behavior
            await bn.spawn(receive_actor, options={"name": "system/receive"})

    logger.debug("closing subprocess")


if __name__ == "__main__":
    trio.run(main)
