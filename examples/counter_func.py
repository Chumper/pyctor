from dataclasses import dataclass

from pyctor.behavior import Behavior, Behaviors, Context, Ref


@dataclass
class Value:
    value: int


class Command:
    pass


class Increment(Command):
    pass


@dataclass
class GetValue(Command):
    reply_to: Ref[Value]


class Counter:
    @staticmethod
    def on_increment(ctx: Context, n: int) -> Behavior[Command]:
        new_value = n + 1
        print(f"Incremented counter to {new_value}")
        return Counter.counter(ctx, new_value)

    @staticmethod
    def on_get_value(n: int, value: GetValue) -> Behavior[Command]:
        value.reply_to.send(Value(n))
        return Behaviors.Same

    @staticmethod
    def counter(ctx: Context[Command], n: int) -> Behavior[Command]:
        def receive(msg: Command) -> Behavior[Command]:
            match msg:
                case Increment():
                    return Counter.on_increment(ctx, n)
                case GetValue() as value:
                    return Counter.on_get_value(n, value)
                case _:
                    return Behaviors.Same

        return Behaviors.receive(receive)

    @staticmethod
    def create() -> Behavior[Command]:
        return Behaviors.setup(lambda ctx: Counter.counter(ctx, 0))
