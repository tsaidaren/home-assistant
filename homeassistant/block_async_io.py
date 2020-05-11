"""Block I/O being done in asyncio."""
from http.client import HTTPConnection
from ssl import SSLContext

from homeassistant.util.async_ import protect_loop


def enable() -> None:
    """Enable the detection of I/O in the event loop."""
    # Prevent urllib3 and requests doing I/O in event loop
    HTTPConnection.putrequest = protect_loop(HTTPConnection.putrequest)
    SSLContext.load_default_certs = protect_loop(SSLContext.load_default_certs)

    # Currently disabled. pytz doing I/O when getting timezone.
    # Prevent files being opened inside the event loop
    # builtins.open = protect_loop(builtins.open)
