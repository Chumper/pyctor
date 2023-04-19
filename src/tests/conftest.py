# create a registry fixture for tests
import pytest
import trio

import pyctor
from pyctor.dispatch.single_process import SingleProcessDispatcher
from pyctor.registry import RegistryImpl
from pyctor.system import BehaviorNurseryImpl


# create a registry fixture for tests
@pytest.fixture
def registry():
    return RegistryImpl("default")


# create a BehaviorNursery fixture for tests
@pytest.fixture
async def behavior_nursery():
    async with pyctor.open_nursery() as nursery:
        yield nursery
