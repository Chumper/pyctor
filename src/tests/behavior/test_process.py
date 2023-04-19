import pytest
import trio

import pyctor
import pyctor.behavior.process
import pyctor.context
import pyctor.registry


@pytest.mark.trio
async def test_behavior():
    # create channel for testing
    send, receive = trio.open_memory_channel(0)

    # create a simple behavior for testing that simply prints the received message
    async def print_behavior(msg: str) -> pyctor.types.Behavior[str]:
        print(msg)
        return pyctor.behaviors.Behaviors.Same

    # create the behavior processor
    b = pyctor.behavior.process.BehaviorProcessorImpl[str](
        behavior=pyctor.Behaviors.receive(print_behavior),
        channel=receive,
        context=pyctor.context.ContextImpl(None),
    )

    # start the behavior processor in a new nursery
    with trio.fail_after(1):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(b.behavior_task)

            # send a message to the behavior
            await send.send("Hello World!")

            # close the channel
            await send.aclose()
