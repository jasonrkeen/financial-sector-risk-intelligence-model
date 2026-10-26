import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Regression tests use synthetic fixtures and must never contact live services."""
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected network request")
    monkeypatch.setattr(socket.socket, "connect", blocked)
