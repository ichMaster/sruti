import asyncio

import pytest

from sruti.receiver import transport


def test_connect_kiwisdr_connects_like_the_browser_with_bounded_messages(monkeypatch):
    calls = {}

    async def fake_connect(url, **kwargs):
        calls["url"], calls["kwargs"] = url, kwargs
        return object()

    monkeypatch.setattr(transport, "fetch_timestamp", lambda host_port: 4611686018427387904 + 42)
    monkeypatch.setattr(transport.websockets, "connect", fake_connect)
    result = asyncio.run(transport.connect_kiwisdr("sdr.example.org:8073"))
    assert isinstance(result, transport.WebSocketTransport)
    assert calls["url"] == "ws://sdr.example.org:8073/ws/no_wf/4611686018427387946/SND"
    assert calls["kwargs"]["max_size"] == transport.MAX_MESSAGE == 1 << 20
    assert calls["kwargs"]["ping_interval"] is None and calls["kwargs"]["compression"] is None


def test_connection_errors_become_transport_closed(monkeypatch):
    def refuse(host_port):
        raise OSError("connection refused")

    monkeypatch.setattr(transport, "fetch_timestamp", refuse)
    with pytest.raises(transport.TransportClosed, match="could not connect"):
        asyncio.run(transport.connect_kiwisdr("sdr.example.org:8073"))
