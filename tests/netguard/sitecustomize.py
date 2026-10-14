"""Block every network connection that does not go to this machine.

Put this directory on PYTHONPATH and any Python process started with it —
the API server, a check script, the CLI — can still talk to 127.0.0.1 but gets
a PermissionError for anything else, including DNS lookups of outside names.
That turns "studying, serving and validating need no network and no model"
from a promise into something a test can fail on (tests/test_determinism.py).
"""
import socket

_LOCAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}
_real_connect = socket.socket.connect
_real_getaddrinfo = socket.getaddrinfo


def _host(address):
    if isinstance(address, tuple) and address:
        return str(address[0])
    return ""  # AF_UNIX path: local by definition


def _connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(address) not in _LOCAL:
        raise PermissionError(f"netguard: external connection blocked: {address!r}")
    return _real_connect(self, address)


def _getaddrinfo(host, *args, **kwargs):
    name = host.decode() if isinstance(host, bytes) else (host or "")
    if name not in _LOCAL:
        raise PermissionError(f"netguard: external lookup blocked: {name!r}")
    return _real_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = _connect
socket.getaddrinfo = _getaddrinfo
