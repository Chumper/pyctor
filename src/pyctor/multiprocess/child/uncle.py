import os
from typing import Any, List, TypeAlias

import cloudpickle  # type: ignore
from msgspec import Struct

import pyctor.behaviors
import pyctor.multiprocess.messages
import pyctor.types


class ChildStopped(Struct):
    """
    A custom watch message that indicates that a child was terminated
    """

    ref: pyctor.types.Ref[Any]


# type alias for easier typing
Messages: TypeAlias = pyctor.multiprocess.messages.SpawnCommand | ChildStopped


class UncleBehavior:
    """
    This behavior is the parent of all behaviors that are requested to be spawned on this subprocess.
    This does not mean that it nessesarily is the logical parent.
    The uncle behavior will be created once the main <-> subprocess connection is established.
    It will only live as long as there are children spawned by this behavior.
    """

    _children: List[pyctor.types.Ref[Any]] = []
    """
    List of all children that are spawned by this behavior
    If the list is empty, the behavior will stop itself
    """

    async def setup(
        self, ctx: pyctor.types.Context[Messages]
    ) -> pyctor.types.BehaviorSetup[Messages]:
        # start a new behavior nursery as we need to spawn children
        async with pyctor.open_nursery() as n:

            # create a new receive behavior
            async def receive(msg: Messages) -> pyctor.types.Behavior[Messages]:
                match msg:
                    # if the msg is a SpawnCommand, spawn the behavior
                    case pyctor.multiprocess.messages.SpawnCommand(
                        reply_to, behavior, options
                    ):
                        print(f"{os.getpid()}: uncle is spawning behavior")
                        decoded_behavior = cloudpickle.loads(behavior)
                        spawned_ref = await n.spawn(
                            behavior=decoded_behavior, options=options
                        )
                        # add to children
                        self._children.append(spawned_ref)
                        # watch the child
                        await ctx.watch(spawned_ref, ChildStopped(spawned_ref))
                        # send the ref back to the orginial spawner
                        reply_to.send(spawned_ref)

                    # if the msg is a ChildStopped, remove the child from the list
                    case ChildStopped(ref):
                        self._children.remove(ref)

                # if there are no more children, stop the behavior
                return (
                    pyctor.behaviors.Behaviors.Same
                    if self._children
                    else pyctor.behaviors.Behaviors.Stop
                )

            # yield the receive behavior
            yield pyctor.behaviors.Behaviors.receive(receive)

    @staticmethod
    def create() -> pyctor.types.BehaviorGeneratorFunction[Messages]:
        return pyctor.behaviors.Behaviors.setup(UncleBehavior().setup)
