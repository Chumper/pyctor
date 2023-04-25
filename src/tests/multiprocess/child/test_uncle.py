
import cloudpickle  # type: ignore
import pytest
import trio
import trio.testing
from msgspec import Struct
from pydantic import BaseModel

import pyctor.behaviors
import pyctor.configuration
import pyctor.multiprocess.messages
import pyctor.registry
import pyctor.testing
from pyctor.multiprocess.child.uncle import UncleBehavior
from pyctor.multiprocess.messages import SpawnCommand


class ReplyMessage(Struct):
    """
    Simple message to test replies
    """
    reply_to: pyctor.types.Ref[str]
    message: str

@pytest.mark.trio
async def test_uncle():

    # create the uncle behavior
    uncle_behavior = UncleBehavior.create()

    # create a simple behavior that will stop after receiving a "stop" message
    # otherwise it will respond with the same message
    async def simple_stopper(msg: ReplyMessage) -> pyctor.types.Behavior[ReplyMessage]:
        if msg.message == "STOP":
            return pyctor.behaviors.Behaviors.Stop
        
        msg.reply_to.send(msg.message)
        return pyctor.behaviors.Behaviors.Stop

    stopper_behavior = pyctor.behaviors.Behaviors.receive(simple_stopper)

    # pickle the behavior with cloudpickle
    pickled_behavior = cloudpickle.dumps(stopper_behavior)

    # fail after 1 second
    # with trio.fail_after(10):
    # create a new behavior nursery
    async with pyctor.open_nursery() as n:
        # spawn the uncle
        uncle_ref = await n.spawn(
            uncle_behavior, options={"name": "subprocess/uncle"}
        )

        # create a test probe
        probe: pyctor.testing.TestProbe[
            pyctor.types.Ref[str]
        ] = await pyctor.testing.TestProbe.create(
            type=pyctor.types.Ref[str], behavior_nursery=n
        )

        # send a message to the uncle to spawn a behavior
        uncle_ref.send(
            SpawnCommand(reply_to=probe.ref, behavior=pickled_behavior)
        )

        # wait for the probe to receive the message
        stopper_ref = await probe.wait()

        # send a message to the stopper so it will reply and ask for a reply
        reply = await stopper_ref.ask(lambda f: ReplyMessage(reply_to=f, message="plase answer"))

        assert reply == "plase answer"

        # send a message to the stopper behavior, so it will stop itself
        stopper_ref.send("STOP")

        # expect the uncle to stop itself


if __name__ == "__main__":
    trio.run(test_uncle)
