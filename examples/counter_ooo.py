# from dataclasses import dataclass
# from typing import final
# from pyctor.behavior import Behavior
# from pyctor.behaviors import Behaviors
# from pyctor.context import Context

# from pyctor.ref import Ref

# @dataclass
# class Value:
#     value: int

# class Command:
#     pass

# @final
# class Increment(Command):
#     pass

# @final
# class GetValue(Command):
#     reply_to: Ref[Value]

# class Counter:

#     @staticmethod
#     def on_increment(ctx: Context, n: int) -> Behavior[Command]:
#         new_value = n + 1
#         print(f"Incremented counter to {new_value}")
#         return Counter.counter(ctx, new_value)

#     @staticmethod
#     def on_get_value(n: int, value: GetValue) -> Behavior[Command]:
#         value.reply_to.send(Value(n))
#         return Behaviors.Same

#     @staticmethod
#     def counter(ctx: Context[Command], n: int) -> Behavior[Command]:
#         return Behaviors.on(Command) \
#             .on_message(Increment, lambda _: Counter.on_increment(ctx, n)) \
#             .on_message(GetValue, lambda command: Counter.on_get_value(n, command)) \
#             .build()
    
#     @staticmethod
#     def create() -> Behavior[Command]:
#         return Behaviors.setup(lambda ctx: Counter.counter(ctx, 0))
