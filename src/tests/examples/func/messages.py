from dataclasses import dataclass

from msgspec import Struct

from pyctor.types import Ref


class PIDRequest(Struct):
    reply_to: Ref[int]
