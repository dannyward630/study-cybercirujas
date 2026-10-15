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


def _connect_ex(self, address):
    # connect_ex reports errors as a return code instead of raising, and it
    # is a separate method: guarding only connect() let a numeric external
    # address through. Same guard, raised, so it cannot be mistaken for a
    # transient network error.
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(address) not in _LOCAL:
        raise PermissionError(f"netguard: external connection blocked: {address!r}")
    return _real_connect_ex(self, address)


_real_connect_ex = socket.socket.connect_ex
socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.getaddrinfo = _getaddrinfo
