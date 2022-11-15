from queue import Queue
from pyctor.types import LifecycleSignal, Mailbox, T


class MailboxImpl(Mailbox[T]):
    _queue: Queue[T | LifecycleSignal]

    def __init__(self, maxsize: int = 10) -> None:
        self._queue = Queue(maxsize=maxsize)

    async def get(self) -> T | LifecycleSignal:
        return self._queue.get(block=True)