import trio


async def main() -> None:
    from trio.testing import open_stream_to_socket_listener

    async with trio.open_nursery() as nursery:
        listeners = await nursery.start(serve_tcp, handler, 0)
        client_stream = await open_stream_to_socket_listener(listeners[0])

        # Then send and receive data on 'client_stream', for example:
        await client_stream.send_all(b"GET / HTTP/1.0\r\n\r\n")
if __name__ == "__main__":
    trio.run(main)
