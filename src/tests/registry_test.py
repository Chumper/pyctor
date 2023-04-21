import pytest
import trio

import pyctor
from pyctor.message_strategies import LOCAL
from pyctor.ref import RefImpl
from pyctor.registry import RegistryImpl
from pyctor.types import Ref, StoppedEvent


@pytest.mark.trio
async def test_init_registry():
    reg = RegistryImpl(name="default")
    assert reg.url == "pyctor://default/"


@pytest.mark.trio
async def test_fallback():
    # open behavior nursery
    async with pyctor.open_nursery() as nursery:
        # create memory channel for the fallback
        fallback_send, fallback_receive = trio.open_memory_channel(1)

        # create new registry
        reg = RegistryImpl(name="default", fallback=fallback_send)

        # create a new channel for the test ref
        test_send, _ = trio.open_memory_channel(0)

        # register the test ref
        ref: Ref[str] = await reg.register(name="test", channel=test_send)

        # deregister the test ref, so it will be removed from the registry
        await reg.deregister(ref)
        # expect the fallback to receive the deregister message
        assert await fallback_receive.receive() == StoppedEvent(ref)


@pytest.mark.trio
async def test_watch_deregister():

    # open behavior nursery
    async with pyctor.open_nursery() as nursery:
        # create a new channel for the test ref
        test_send, _ = trio.open_memory_channel(0)

        # create new registry
        reg = RegistryImpl(name="default")

        # register the test ref
        ref: Ref[str] = await reg.register(name="test", channel=test_send)

        # create a new channel for the watcher
        watcher_send, watcher_receive = trio.open_memory_channel(0)

        # create a new ref for the watcher
        watcher: Ref[str] = await reg.register(name="watcher", channel=watcher_send)

        # watch the test ref with a simple string message
        await reg.watch(ref, watcher, "terminated")

        # deregister the test ref, so it will be removed from the registry and the watcher will receive the message
        await reg.deregister(ref)

        # expect the watcher to receive the message
        assert await watcher_receive.receive() == "terminated"


@pytest.mark.trio
async def test_watch_nonexistent():
    # open behavior nursery
    async with pyctor.open_nursery() as nursery:

        # create a new channel for the watcher
        watcher_send, watcher_receive = trio.open_memory_channel(0)

        # create new registry
        reg = RegistryImpl(name="default")

        # create a new ref for the watcher
        watcher: Ref[str] = await reg.register(name="watcher2", channel=watcher_send)

        # create a bogus ref
        bogus_ref = RefImpl(registry=reg.url, name="bogus", strategy=LOCAL, managing_registry=reg)

        # watch a nonexistent ref with a simple string message
        await reg.watch(bogus_ref, watcher, "terminated")

        # expect the watcher to receive the message
        assert await watcher_receive.receive() == "terminated"


# test when deregister ref is the fallback
@pytest.mark.trio
async def test_watch_deregister_fallback():
    # open behavior nursery
    async with pyctor.open_nursery() as nursery:
        # create memory channel for the fallback
        fallback_send, fallback_receive = trio.open_memory_channel(1)

        # create new registry
        reg = RegistryImpl(name="default", fallback=fallback_send)
