import trio


async def main() -> None:
    print("subprocess executed")


if __name__ == "__main__":
    trio.run(main)
