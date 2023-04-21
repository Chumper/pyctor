# test the send behavior of the child process
#
# this test will spawn a child process and send a message to it
# the child process will then send the message back to the parent process
# the parent process will then check if the message is the same as the one it sent
# the child process will then send a stop command to the parent process
# the parent process will then check if the child process has stopped

from typing import Any
import msgspec
import trio
import trio.testing
import pytest

import cloudpickle # type: ignore

import pyctor.configuration
import pyctor.testing
import pyctor.behaviors

from pyctor.multiprocess.child.send import MultiProcessChildConnectionSendActor
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

@pytest.mark.trio
async def test_send_behavior():

    # get the default encoder
    encoder = msgspec.msgpack.Encoder(
        enc_hook=encode_func(pyctor.configuration._custom_encoder_function)
    )

    # get the default decoder
    decoder = msgspec.msgpack.Decoder(
        dec_hook=decode_func(pyctor.configuration._custom_decoder_function)
    )

    # create a new memory stream for testing
    send_stream, receive_stream = trio.testing.memory_stream_pair()

    # create a new send behavior
    behavior = MultiProcessChildConnectionSendActor.create(
        stream=send,
        encoder=msgspec.msgpack.Encoder(enc_hook=pyctor.configuration._default_encoder),
    )

    # create a simple behavior that will stop after receiving a string message
    async def simple_stopper(msg: str) -> pyctor.types.Behavior[str]:
        return pyctor.behaviors.Behaviors.Stop
    
    behavior = pyctor.behaviors.Behaviors.receive(simple_stopper)
    
    # pickle the behavior with cloudpickle
    pickled_behavior = cloudpickle.dumps(behavior) 

    # create a new test probe
    probe = pyctor.testing.TestProbe()

    # create a new behavior nursery
    async with pyctor.open_nursery() as n:
        # spawn the behavior
        ref = await n.spawn(behavior=behavior, options={ "name": "send_test" })

        # send a message through the stream
        send(send_stream, SpawnCommand(reply_to=probe, behavior=pickled_behavior), encoder)

