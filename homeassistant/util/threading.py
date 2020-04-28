"""Threading util helpers."""
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

    init_old = threading.Thread.__init__

    def init_new(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Patch threading init to call excepthook when run has an uncaught exception."""
        init_old(self, *args, **kwargs)
        run_old = self.run

        def run_with_our_excepthook(*args: Any, **kwargs: Any) -> Any:
            try:
                run_old(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):  # pylint: disable=try-except-raise
                raise
            except Exception:  # pylint: disable=broad-except
                sys.excepthook(*sys.exc_info())

        self.run = run_with_our_excepthook

    threading.Thread.__init__ = init_new  # type: ignore
