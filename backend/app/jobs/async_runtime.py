import asyncio
import os
import threading
from collections.abc import Awaitable
from typing import TypeVar


T = TypeVar("T")

_loop_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_loop_pid: int | None = None


def _start_loop_for_pid(pid: int) -> asyncio.AbstractEventLoop:
    started = threading.Event()
    holder: dict[str, asyncio.AbstractEventLoop] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        holder["loop"] = loop
        started.set()
        loop.run_forever()

    thread = threading.Thread(target=_runner, name="celery-async-runtime", daemon=True)
    thread.start()
    started.wait(timeout=5)
    loop = holder.get("loop")
    if loop is None:
        raise RuntimeError("Failed to initialize async runtime loop")

    global _loop, _loop_thread, _loop_pid
    _loop = loop
    _loop_thread = thread
    _loop_pid = pid
    return loop


def _get_loop() -> asyncio.AbstractEventLoop:
    pid = os.getpid()
    with _loop_lock:
        if _loop is not None and _loop_pid == pid and _loop.is_running():
            return _loop
        return _start_loop_for_pid(pid)


def run_async(awaitable: Awaitable[T]) -> T:
    loop = _get_loop()
    future = asyncio.run_coroutine_threadsafe(awaitable, loop)
    return future.result()
