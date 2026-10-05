import pytest

from utils.middleware import RequestLimitsMiddleware


@pytest.mark.parametrize("chunks,expected", [([b"abc", b"def"], 200), ([b"abcd", b"efg"], 413)])
async def test_chunked_body_is_bounded_before_application(chunks, expected):
    messages = [
        {"type": "http.request", "body": chunk, "more_body": i < len(chunks) - 1}
        for i, chunk in enumerate(chunks)
    ]
    sent = []
    received = []

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        received.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    await RequestLimitsMiddleware(app, max_bytes=6)(
        {"type": "http", "method": "POST", "path": "/combo", "headers": []}, receive, send
    )
    assert sent[0]["status"] == expected
    if expected == 200:
        assert received[0]["body"] == b"abcdef"
        assert dict(sent[0]["headers"])[b"cache-control"] == b"no-store"
    else:
        assert received == []


@pytest.mark.parametrize(
    "host,expected",
    [
        (b"[::1]:8000", 200),
        (b"[::1]", 200),
        (b"[::2]:8000", 400),
        (b"evil.example", 400),
        (b"evil@[::1]", 400),
        (b"[::1]:bad", 400),
        (b"[::1]/path", 400),
        (b"[::1]#evil", 400),
        (b"\xff", 400),
    ],
)
async def test_ipv6_host_validation(host, expected):
    from utils.middleware import ConfiguredHostMiddleware

    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    await ConfiguredHostMiddleware(app, "http://[::1]:8000")(
        {"type": "http", "method": "GET", "path": "/health", "headers": [(b"host", host)]},
        receive,
        send,
    )
    assert sent[0]["status"] == expected


async def test_duplicate_hosts_are_rejected():
    from utils.middleware import ConfiguredHostMiddleware

    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        pytest.fail("Ambiguous host reached application")

    await ConfiguredHostMiddleware(app, "http://localhost:8000")(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"host", b"localhost"), (b"host", b"evil")],
        },
        receive,
        send,
    )
    assert sent[0]["status"] == 400
