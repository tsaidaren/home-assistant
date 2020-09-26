"""Threading util helpers."""
import ctypes
import inspect
import sys
import threading
from typing import Any


def fix_threading_exception_logging() -> None:
    """Fix threads passing uncaught exceptions to our exception hook.

    https://bugs.python.org/issue1230540
    Fixed in Python 3.8.
    """
    if sys.version_info[:2] >= (3, 8):
        return

    run_old = threading.Thread.run

    def run(*args: Any, **kwargs: Any) -> None:
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):  # pylint: disable=try-except-raise
            raise
        except Exception:  # pylint: disable=broad-except
            sys.excepthook(*sys.exc_info())

    threading.Thread.run = run  # type: ignore


def _async_raise(tid: int, exctype: Any) -> None:
    """Raise an exception in the threads with id tid."""
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(tid), ctypes.py_object(exctype)
    )
    if res == 0:
        raise ValueError("Invalid thread id")
    elif res != 1:
        # "if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class ThreadWithException(threading.Thread):
    """A thread class that supports raising exception in the thread from another thread.

    Based on
    https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread/49877671

    """

    def raise_exc(self, exctype: Any) -> None:
        """Raise the given exception type in the context of this thread.

        If the thread is busy in a system call (time.sleep(),
        socket.accept(), ...), the exception is simply ignored.

        If you are sure that your exception should terminate the thread,
        one way to ensure that it works is:

            t = ThreadWithException( ... )
            ...
            t.raise_exc( SomeException )
            while t.isAlive():
                time.sleep( 0.1 )
                t.raise_exc( SomeException )

        If the exception is to be caught by the thread, you need a way to
        check that your thread has caught it.

        CAREFUL : this function is executed in the context of the
        caller thread, to raise an exception in the context of the
        thread represented by this instance.
        """
        _async_raise(threading.get_ident(), exctype)
