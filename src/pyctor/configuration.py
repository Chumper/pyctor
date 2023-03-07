from typing import Any, Callable, Type

import msgspec

import pyctor.defaults
import pyctor.multiprocess.messages

_custom_encoder_function: Callable[[Any], Any] = pyctor.defaults.default_custom_encoder_function
_custom_decoder_function: Callable[[Type, Any], Any] = pyctor.defaults.default_custom_decoder_function

_default_encoder: msgspec.msgpack.Encoder = msgspec.msgpack.Encoder(enc_hook=_custom_encoder_function)

def set_custom_encoder_function(func: Callable[[Any], Any]) -> None:
    global _custom_encoder_function
    global _default_encoder
    _custom_encoder_function = func
    _default_encoder = msgspec.msgpack.Encoder(enc_hook=pyctor.multiprocess.messages.encode_func(func=func))

def set_custom_decoder_function(func: Callable[[Type, Any], Any]) -> None:
    global _custom_decoder_function
    _custom_decoder_function = func