"""Small setup requests are bounded before any form parser runs."""

from urllib.parse import urlsplit

from starlette.responses import PlainTextResponse


class RequestLimitsMiddleware:
    def __init__(self, app, max_bytes=16384):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await PlainTextResponse("Invalid content length", status_code=400)(
                scope, receive, send
            )
        if length < 0 or length > self.max_bytes:
            return await PlainTextResponse("Request too large", status_code=413)(
                scope, receive, send
            )
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                return await PlainTextResponse("Request too large", status_code=413)(
                    scope, receive, send
                )
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'none'; style-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'",
                    ),
                ]
            await send(message)

        await self.app(scope, replay, secured_send)


class ConfiguredHostMiddleware:
    """Validate the configured hostname, including bracketed IPv6 loopback."""

    def __init__(self, app, origin):
        self.app = app
        self.hostname = urlsplit(origin).hostname

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        hosts = [value for key, value in scope["headers"] if key.lower() == b"host"]
        valid = False
        if len(hosts) == 1:
            try:
                parts = urlsplit("//" + hosts[0].decode("ascii"))
                _ = parts.port  # Validate the port representation too.
                valid = parts.hostname == self.hostname and not (
                    parts.username or parts.password or parts.path or parts.query or parts.fragment
                )
            except (ValueError, UnicodeDecodeError):
                pass
        if not valid:
            return await PlainTextResponse("Invalid host header", status_code=400)(
                scope, receive, send
            )
        await self.app(scope, receive, send)
