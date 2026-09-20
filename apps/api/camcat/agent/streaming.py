from collections.abc import Callable, Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from threading import BoundedSemaphore

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="camcat-agent")
_capacity = BoundedSemaphore(8)


def background_stream(produce: Callable[[], Iterable[str]]) -> Generator[str, None, None]:
    """Keep bounded agent work alive after a client disconnects; emit idle heartbeats."""
    if not _capacity.acquire(blocking=False):
        raise RuntimeError("Agent 队列已满，请稍后重试")
    messages: Queue[str | Exception | None] = Queue()

    def run() -> None:
        try:
            for message in produce():
                messages.put(message)
        except Exception as exc:
            messages.put(exc)
        finally:
            messages.put(None)
            _capacity.release()

    try:
        _executor.submit(run)
    except Exception:
        _capacity.release()
        raise

    def consume() -> Generator[str, None, None]:
        while True:
            try:
                message = messages.get(timeout=10)
            except Empty:
                yield ": heartbeat\n\n"
                continue
            if message is None:
                return
            if isinstance(message, Exception):
                raise message
            yield message

    return consume()
