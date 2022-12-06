
from dataclasses import dataclass
from typing import Generic

import pyctor.types

class MultiProcessBase():
    pass

@dataclass
class SpawnRequest(MultiProcessBase, Generic[pyctor.types.T]):
    reply_to: pyctor.types.Ref[pyctor.types.Ref[pyctor.types.T]]
    behavior: pyctor.types.BehaviorGeneratorFunction[pyctor.types.T]
    name: str
    core: int # represents the core that the behavior should be spawned on

@dataclass
class ProcessMessage(MultiProcessBase, Generic[pyctor.types.T]):
    url: str
    msg: pyctor.types.T