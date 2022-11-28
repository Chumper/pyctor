from typing import Annotated, Generic, TypeVar
from msgspec import Meta, Struct
import msgspec
import trio

# A float constrained to values > 0
PositiveFloat = Annotated[float, Meta(gt=0)]

T = TypeVar("T")

class Dimensions(Generic[T], Struct):
    """Dimensions for a product, all measurements in centimeters"""
    length: PositiveFloat
    width: PositiveFloat
    height: PositiveFloat
    def do_stuff(self, msg: T) -> None:
        pass

async def main() -> None:
    print("subprocess executed")
    t = Dimensions[str](length=1.0, width=1.0, height=1.0)
    # reveal_type(t)
    print(msgspec.json.encode(t))

if __name__ == "__main__":
    trio.run(main)
