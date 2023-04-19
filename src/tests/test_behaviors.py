# test that the beahaviors are type checking the passed functions

import typeguard

from pyctor.behaviors import Behaviors
from pyctor.types import Behavior


def test_behaviors_receive_number():
    try:
        Behaviors.receive(1)
    except typeguard.TypeCheckError:
        pass
    else:
        raise AssertionError("TypeError not raised")


def test_behaviors_receive_wrong_function():
    def f():
        return 1

    try:
        Behaviors.receive(f)
    except typeguard.TypeCheckError:
        pass
    else:
        raise AssertionError("TypeError not raised")


def test_behaviors_receive_correct_function():
    def f(x: str) -> Behavior[str]:
        return Behaviors.Same

    try:
        Behaviors.receive(f)
    except TypeError:
        raise AssertionError("TypeError raised")
