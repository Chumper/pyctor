# #!/usr/bin/env python3


# from pyctor.behavior import Behavior
# from pyctor.behaviors import Behaviors
# from pyctor.context import Context


# class Protocol:
#     pass


# class Request1(Protocol):
#     pass


# class Request2(Protocol):
#     pass

# def setup(ctx: Context[Protocol]) -> Behavior[Protocol]:
#     # childRef = ctx.spawn()
#     ref = ctx.self()
#     return Behaviors.Same

# def receive_context(ctx: Context[Protocol], msg: Protocol) -> Behavior[Protocol]:
#     # childRef = ctx.spawn()
#     ref = ctx.self()
#     pass

# def receive(msg: Protocol) -> Behavior[Protocol]:
#     # childRef = ctx.spawn()
#     match msg:
#         case Request1():
#             print("request1")


# def main() -> None:
#     setup_behavior = Behaviors.setup(setup)
#     msg_behavior = Behaviors.receive(receive)
#     ctx_behavior = Behaviors.receive_context(receive_context)

# if __name__ == "__main__":
#     main()
