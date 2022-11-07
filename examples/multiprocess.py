
import trio
from multiprocessing import Process

def f(name):
    print('hello', name)

async def main():
    p = Process(target=f, args=('bob',))
    p.start()
    p.join()

if __name__ == "__main__":
    trio.run(main)