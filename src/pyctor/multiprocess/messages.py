import builtins
import sys
from typing import Any, Callable, Optional, Type

from msgspec import Raw, Struct

import pyctor.ref
import pyctor.system
import pyctor.types


class MultiProcessMessage(Struct, tag_field="msg_type", tag=str.lower):
    pass


class SpawnCommand(MultiProcessMessage):
    reply_to: pyctor.types.Ref[pyctor.types.Ref[Any]]
    behavior: bytes
    options: Optional[pyctor.types.SpawnOptions] = None


class StopCommand(MultiProcessMessage):
    ref: pyctor.types.Ref[Any]


class MessageCommand(MultiProcessMessage):
    ref: pyctor.types.Ref[Any]
    type: str
    msg: Raw


def get_type(type_name: str):
    try:
        module, name = type_name.rsplit(".", maxsplit=1)
        return getattr(builtins, name)
    except AttributeError:
        try:
            obj = getattr(sys.modules[module], name, None)
        except KeyError:
            return None
        return obj


def encode_func(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def encode_message(obj: Any) -> Any:

        print(f"Encode type {type(obj)}: {obj}")
        # encode ref
        if isinstance(obj, pyctor.ref.RefImpl):
            print(str(obj.registry), str(obj.name))
            return (obj.registry, obj.name)

        # call custom encoder
        data = func(obj)
        if not data:
            raise TypeError(f"Objects of type {type(obj)} are not supported")
        return data

    return encode_message


def decode_func(func: Callable[[Type, Any], Any]) -> Callable[[Type, Any], Any]:
    def decode_message(my_type: Type, obj: Any) -> Any:
        # decode ref
        print(f"Decode type {my_type}: {obj}")
        registry: pyctor.types.Registry = pyctor.system.registry.get()
        if my_type == pyctor.ref.RefImpl:
            return registry.ref_from_raw(obj[0], obj[1])
        if str(my_type).startswith("pyctor.types.Ref["):
            return registry.ref_from_raw(obj[0], obj[1])

        # call custom decoder
        data = func(my_type, obj)
        if not data:
            raise TypeError(f"Objects of type {my_type} are not supported")
        return data

    return decode_message
