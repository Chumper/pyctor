# test the send behavior of the child process
#
# this test will spawn a child process and send a message to it
# the child process will then send the message back to the parent process
# the parent process will then check if the message is the same as the one it sent
# the child process will then send a stop command to the parent process
# the parent process will then check if the child process has stopped

from typing import Any

import cloudpickle  # type: ignore
import msgspec
import pytest
import tricycle
import trio
import trio.testing

import pyctor.behaviors
import pyctor.configuration
import pyctor.registry
import pyctor.testing
from pyctor.multiprocess.child.receive import MultiProcessChildConnectionReceiveBehavior
from pyctor.multiprocess.messages import SpawnCommand, decode_func, encode_func


# helper function to send a message through the stream
async def send(channel: trio.abc.SendStream, msg: Any, encoder: msgspec.msgpack.Encoder) -> None:
    # decode the message
    buffer = encoder.encode(msg)
    # convert the length of the buffer to bytes
    prefix = len(buffer).to_bytes(4, "big")

    # send the prefix and the buffer
    await channel.send_all(prefix)
    await channel.send_all(buffer)
    print("Send message: ", msg, " with prefix: ", prefix)


@pytest.mark.trio
async def test_receive_behavior():

    # get the default encoder
    encoder = msgspec.msgpack.Encoder(enc_hook=encode_func(pyctor.configuration._custom_encoder_function))

    # get the default decoder
    decoder = msgspec.msgpack.Decoder(dec_hook=decode_func(pyctor.configuration._custom_decoder_function))

    # create a new memory stream for testing
    send_stream, receive_stream = trio.testing.memory_stream_pair()
    buffered_receive_stream = tricycle.BufferedReceiveStream(transport_stream=receive_stream)

    # create a new registry for this test
    registry = pyctor.registry.RegistryImpl()

    # create a new receive behavior
    child_receive_behavior = MultiProcessChildConnectionReceiveBehavior.create(
        stream=buffered_receive_stream,
        decoder=decoder,
        registry=registry,
    )

    # create a simple behavior that will stop after receiving a string message
    async def simple_stopper(msg: str) -> pyctor.types.Behavior[str]:
        return pyctor.behaviors.Behaviors.Stop

    stopper_behavior = pyctor.behaviors.Behaviors.receive(simple_stopper)

    # pickle the behavior with cloudpickle
    pickled_behavior = cloudpickle.dumps(stopper_behavior)

    # fail after 1 second
    with trio.fail_after(2):
        # create a new behavior nursery
        async with pyctor.open_nursery() as n:
            # spawn the child receive behavior
            child_receive_ref = await n.spawn(child_receive_behavior, options={"name": "child/receive"})

            # create a test probe
            probe: pyctor.testing.TestProbe[pyctor.types.Ref[str]] = await pyctor.testing.TestProbe.create(type=pyctor.types.Ref[str], behavior_nursery=n)

            # send a message through the stream to spawn the stopper behavior
            # await send(send_stream, SpawnCommand(reply_to=probe.ref, behavior=pickled_behavior), encoder)

            # send a message to the behavior and spawn the stopper behavior
            child_receive_ref.send(SpawnCommand(reply_to=probe.ref, behavior=pickled_behavior))

            await trio.sleep(0.5)
            ref = probe.messages[0]

            # send a message to the stopper behavior
            ref.send("stop")

            # # wait for the probe to receive the message
            # await trio.sleep(0.5)
            # assert probe.messages == []
