import msgspec


class Test(msgspec.Struct):
    data: msgspec.Raw


t = Test()
