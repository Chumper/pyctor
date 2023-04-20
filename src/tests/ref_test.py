import pyctor.types
from pyctor.message_strategies import LOCAL
from pyctor.ref import RefImpl


def test_create_ref(registry: pyctor.types.Registry):
    # create a ref
    ref: pyctor.types.Ref[str] = RefImpl(registry=registry.url, name="test", strategy=LOCAL, managing_registry=registry)
    # check that the url matches the registry url + name
    assert ref.url == registry.url + "test"
