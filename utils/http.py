"""Bounded retries for provider reads and Combo's idempotent revenue updates."""

import asyncio

import httpx

from utils.config import settings


async def request_json(
    client: httpx.AsyncClient, method: str, path: str, *, retry_safe: bool = True, **kwargs
):
    attempts = settings.HTTP_RETRIES + 1 if retry_safe else 1
    for attempt in range(attempts):
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.TransportError:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(min(2**attempt, 5))
            continue
        if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
            try:
                delay = float(response.headers.get("Retry-After", 2**attempt))
            except ValueError:
                delay = 2**attempt
            await asyncio.sleep(max(0, min(delay, 5)))
            continue
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("errors"):
            raise ValueError("Provider reported an API error")
        return payload
    raise RuntimeError("Provider request did not complete")  # defensive


def safe_error(error: Exception) -> str:
    """Never copy provider responses, credentials or user-controlled URLs into logs."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"Provider HTTP {error.response.status_code}"
    return type(error).__name__
