"""Microservice helper functions for generated Python code.

Uses httpx for HTTP calls, tenacity for retry/backoff, pybreaker for circuit breakers.
Service URLs are resolved from the config store peer-URL namespace (no env reads).
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import enum
import functools
import inspect
import json
import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Protocol

import httpx
import pybreaker
import tenacity

logger = logging.getLogger(__name__)

from ._service_credential import acquire_service_credential


async def _inter_service_auth_headers() -> dict[str, str]:
    """Bearer credential for raw HTTP calls to peer services (managed machine identity).

    The credential's audience is the machine identity provider's own resource,
    resolved inside ``acquire_service_credential`` — never the callee's network
    address. Fails closed: a token-acquisition failure raises rather than returning
    empty headers — an unauthenticated peer call is never emitted (design principle 15).
    """
    token = await acquire_service_credential()
    return {"Authorization": f"Bearer {token}"}


# ── Service URL resolution ──


def _json_default(value: object) -> object:
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json", by_alias=True)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_serialize(value: object) -> str:
    return json.dumps(value, default=_json_default)


def _json_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(headers or {})
    merged.setdefault("Content-Type", "application/json")
    return merged


class PageWindowError(ValueError):
    """A ``PageRequest`` cannot be addressed in the provider's pagination pair."""


class PageWindowLike(Protocol):
    """What the conversion reads of a ``PageRequest``: its row window."""

    offset: int
    limit: int


def _ms_page_window(
    page: PageWindowLike, offset_wire: str, limit_wire: str, *, page_index: bool
) -> dict[str, int]:
    """Query entries sending *page* in the provider's offset/limit pair.

    A provider whose position counts pages is addressed by ``offset // limit``; an
    offset that is not a whole number of pages is refused with
    :class:`PageWindowError` rather than floored onto a different window.

    Args:
        page: The row-semantic request.
        offset_wire: The provider's position parameter name.
        limit_wire: The provider's size parameter name.
        page_index: True when the provider's position counts pages, not rows.

    Returns:
        The two query entries.

    Raises:
        PageWindowError: *page_index* is true and the offset is not a multiple of
            the limit.
    """
    if not page_index:
        return {offset_wire: page.offset, limit_wire: page.limit}
    if page.offset % page.limit != 0:
        raise PageWindowError(
            f"PageRequest offset {page.offset} is not a whole number of pages of "
            f"{page.limit} rows; the provider addresses pages by index. Request an "
            f"offset that is a multiple of the limit."
        )
    return {offset_wire: page.offset // page.limit, limit_wire: page.limit}


_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_microservice_http_timeout: ContextVar[float | None] = ContextVar(
    "microservice_http_timeout", default=None
)


_MS_DEFAULT_TIMEOUT: float = 30.0


def _http_client(**kwargs: object) -> httpx.AsyncClient:
    timeout = _microservice_http_timeout.get()
    if timeout is not None and "timeout" not in kwargs:
        kwargs["timeout"] = timeout
    elif "timeout" not in kwargs:
        kwargs["timeout"] = _MS_DEFAULT_TIMEOUT
    return httpx.AsyncClient(**kwargs)


class PeerCallError(Exception):
    """A call to a peer service failed: names the peer, the route and the status.

    Never the resolved URL, host or port: the library error, whose text carries
    the address, is neither chained nor logged. ``status`` is ``None`` when the
    peer gave no response (a refused connection, a timeout).
    """

    def __init__(self, service: str, route: str, status: int | None) -> None:
        self.service = service
        self.route = route
        self.status = status
        outcome = f"status {status}" if status is not None else "no response"
        super().__init__(
            f"Call to service '{service}' route '{route}' failed: {outcome}."
        )


class HttpPostError(Exception):
    """A POST with explicit headers got no response: never the URL or those headers.

    A status is an answer, returned to the caller; only a call that reached no
    server raises, and its library error, which carries the URL, is not chained.
    """

    def __init__(self) -> None:
        super().__init__("HTTP POST failed: no response.")


def _raise_for_status_with_body(
    response: httpx.Response, service: str, route: str
) -> None:
    """Raise ``PeerCallError`` on an error status, first logging the peer and route -- never the resolved URL."""
    if response.status_code >= 400:
        logger.error(
            "inter_service_http_failed service=%s route=%s status=%s body=%s",
            service,
            route,
            response.status_code,
            response.text[:500],
        )
        raise PeerCallError(service, route, response.status_code)


async def _peer_send(
    service: str,
    route: str,
    method: str,
    url: str,
    client_kwargs: dict[str, object] | None = None,
    **request_kwargs: object,
) -> object:
    """Send one request to peer *service* and answer its JSON body.

    Raises:
        PeerCallError: The peer answered an error status, or gave no response.
    """
    try:
        async with _http_client(**(client_kwargs or {})) as client:
            response = await client.request(method, url, **request_kwargs)
    except httpx.HTTPError as exc:
        logger.error(
            "inter_service_http_unreachable service=%s route=%s error=%s",
            service,
            route,
            type(exc).__name__,
        )
        raise PeerCallError(service, route, None) from None
    _raise_for_status_with_body(response, service, route)
    return response.json()


async def _await_if_needed(value: object) -> object:
    if inspect.isawaitable(value):
        return await value
    return value


# The AppSettings attribute carrying each declared dependency's base URL, under every
# name the dependency is addressed by (its qualified and its simple kebab-case name).
_PEER_URL_SETTINGS: dict[str, str] = {
    "cityservices-district-service": "cityservices_district_service_service_url",
    "district-service": "cityservices_district_service_service_url",
}

# One name per declared dependency: the one ``listServices`` reports it under.
_DECLARED_PEERS: tuple[str, ...] = ("cityservices-district-service",)

# Peers registered at runtime (``Microservice.register``); they take precedence over the
# declared dependencies.
_SERVICE_URLS: dict[str, str] = {}


def _normalize_service_name(service: str) -> str:
    """The registry key of *service*: trimmed, lower-cased, underscores as hyphens."""
    return service.strip().lower().replace("_", "-")


def _register_service_url(service: str, url: str) -> None:
    """Register a peer service URL at runtime, ahead of any declared one."""
    _SERVICE_URLS[_normalize_service_name(service)] = url


def _known_services() -> list[str]:
    """Every declared dependency (one name each) and every runtime-registered peer, sorted."""
    return sorted({*_DECLARED_PEERS, *_SERVICE_URLS})


def _resolve_service_url(service: str) -> str:
    """Resolve a peer service base URL: a runtime registration, else the declared dependency's setting.

    The declared value is read from the assembled AppSettings (the config-store
    ``connections`` namespace). No environment reads are performed.

    Raises:
        RuntimeError: *service* is neither registered nor a declared dependency, or its
            base URL is empty in the assembled settings.
    """
    name = _normalize_service_name(service)
    registered = _SERVICE_URLS.get(name)
    if registered is not None:
        return registered
    if name not in _PEER_URL_SETTINGS:
        raise RuntimeError(
            f"Service URL for '{service}' not configured: it is neither a declared dependency "
            f"nor registered. Known: {', '.join(_known_services()) or '(none)'}."
        )
    from cityservices_request_service.config.settings import get_settings

    url = getattr(get_settings(), _PEER_URL_SETTINGS[name])
    if not url:
        raise RuntimeError(
            f"Service URL for '{service}' is empty in the assembled settings."
        )
    return str(url)


# ── HTTP call methods ──


async def _ms_call(service: str, method: str, params: dict | None = None) -> object:
    """Call service method via HTTP POST."""
    url = f"{_resolve_service_url(service)}/{method}"
    headers = _json_headers(await _inter_service_auth_headers())
    return await _peer_send(
        service,
        f"/{method}",
        "POST",
        url,
        content=_json_serialize(params or {}),
        headers=headers,
    )


#: Fire-and-forget calls still in flight. The event loop holds a task only
#: weakly, so an unreferenced call could be collected before it finishes.
_PENDING_ASYNC_CALLS: set[asyncio.Task[object]] = set()


def _finish_async_call(service: str, method: str, task: asyncio.Task[object]) -> None:
    """Release a finished fire-and-forget call, logging its failure: no caller is waiting to see it.

    The log names the peer, the endpoint and the error's class, never the
    error's text, which carries the peer's internal address.
    """
    _PENDING_ASYNC_CALLS.discard(task)
    if task.cancelled():
        logger.warning("call_async_cancelled service=%s endpoint=%s", service, method)
        return
    error = task.exception()
    if error is not None:
        logger.warning(
            "call_async_failed service=%s endpoint=%s error=%s",
            service,
            method,
            type(error).__name__,
        )


async def _ms_call_async(service: str, method: str, params: dict | None = None) -> None:
    """Fire-and-forget service call: the caller does not wait, and a failure is logged, never raised."""
    task = asyncio.create_task(_ms_call(service, method, params))
    _PENDING_ASYNC_CALLS.add(task)
    task.add_done_callback(functools.partial(_finish_async_call, service, method))


async def _ms_post(service: str, endpoint: str, data: object) -> object:
    url = f"{_resolve_service_url(service)}{endpoint}"
    headers = _json_headers(await _inter_service_auth_headers())
    return await _peer_send(
        service, endpoint, "POST", url, content=_json_serialize(data), headers=headers
    )


async def _ms_put(service: str, endpoint: str, data: object) -> object:
    url = f"{_resolve_service_url(service)}{endpoint}"
    headers = _json_headers(await _inter_service_auth_headers())
    return await _peer_send(
        service, endpoint, "PUT", url, content=_json_serialize(data), headers=headers
    )


async def _ms_delete(service: str, endpoint: str) -> object:
    url = f"{_resolve_service_url(service)}{endpoint}"
    headers = await _inter_service_auth_headers()
    return await _peer_send(service, endpoint, "DELETE", url, headers=headers)


async def _http_post_with_headers(
    url: str, body: str, headers: dict[str, str]
) -> dict[str, object]:
    """POST a UTF-8 string body with explicit headers (e.g. webhooks with HMAC).

    Returns a dict with ``statusCode`` (HTTP status) and ``body`` (parsed JSON or
    ``None`` if the response is not valid JSON). Does not raise on 4xx/5xx.

    Raises:
        HttpPostError: The server gave no response.
    """
    try:
        async with _http_client() as client:
            response = await client.post(
                url, content=body.encode("utf-8"), headers=headers
            )
    except httpx.HTTPError as exc:
        logger.error("http_post_unreachable error=%s", type(exc).__name__)
        raise HttpPostError() from None
    try:
        parsed: object = response.json()
    except Exception:
        parsed = None
    return {"statusCode": response.status_code, "body": parsed}


async def _http_post_webhook(
    url: str, body: str, signature: str, delivery_id: str
) -> dict[str, object]:
    """POST JSON webhook with standard HMAC and tracing headers."""
    headers = {
        "X-Webhook-Signature": signature,
        "X-Webhook-Id": delivery_id,
        "Content-Type": "application/json",
    }
    return await _http_post_with_headers(url, body, headers)


async def _ms_call_with_options(service: str, endpoint: str, options: dict) -> object:
    url = f"{_resolve_service_url(service)}{endpoint}"
    opts = dict(options)
    timeout = opts.pop("timeout", None)
    extra_headers = opts.pop("headers", None)
    method = opts.pop("method", "GET")
    if opts:
        raise ValueError(
            f"Unknown Microservice.callWithOptions option(s) {sorted(opts)}; "
            "supported: ['headers', 'method', 'timeout']"
        )
    merged_headers: dict[str, str] = dict(await _inter_service_auth_headers())
    if extra_headers:
        merged_headers.update(extra_headers)
    client_kwargs: dict[str, object] = {"headers": merged_headers}
    if timeout is not None:
        client_kwargs["timeout"] = timeout
    return await _peer_send(service, endpoint, method, url, client_kwargs)


# ── Service discovery ──


async def _ms_discover(service: str) -> dict[str, object]:
    return {"name": service, "url": _resolve_service_url(service)}


_PEER_STATUS_UP = "up"
_PEER_STATUS_DOWN = "down"


async def _ms_health(service: str) -> dict[str, str]:
    """The health of peer *service* (a ``HealthStatus``): ``{"status": "up"}`` or ``{"status": "down"}``.

    Up when the peer's ``/health`` answers a 2xx status within the declared client
    timeout; any other outcome -- an error status, a timeout, a refused connection
    -- is down. The failure is logged here by its class and never returned: its
    text names the peer's internal host and port.
    """
    url = f"{_resolve_service_url(service)}/health"
    try:
        async with _http_client() as client:
            response = await client.get(url)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 -- a failed peer probe is recorded as down
        logger.warning(
            "peer_health_down service=%s error=%s", service, type(exc).__name__
        )
        return {"status": _PEER_STATUS_DOWN}
    return {"status": _PEER_STATUS_UP}


async def _ms_register(service: str, endpoint: str) -> None:
    """Register a peer service URL in the in-process registry."""
    _register_service_url(service, endpoint)


async def _ms_deregister(service: str) -> None:
    """Remove a peer service URL from the in-process registry."""
    _SERVICE_URLS.pop(_normalize_service_name(service), None)


def _ms_get_url(service: str) -> str:
    return _resolve_service_url(service)


async def _ms_is_available(service: str) -> bool:
    """Whether peer *service* is up (see :func:`_ms_health`)."""
    return (await _ms_health(service))["status"] == _PEER_STATUS_UP


def _ms_list_services() -> list[str]:
    """Every declared dependency (one name each) and every runtime-registered peer, sorted."""
    return _known_services()


async def _ms_health_check_all() -> dict[str, dict[str, str]]:
    """The health of every known peer, probed concurrently: a down peer is recorded, never raised."""
    services = _ms_list_services()
    statuses = await asyncio.gather(*(_ms_health(svc) for svc in services))
    return dict(zip(services, statuses, strict=True))


# ── Resilience patterns ──

_circuit_breakers: dict[str, pybreaker.CircuitBreaker] = {}


def _get_circuit_breaker(service: str) -> pybreaker.CircuitBreaker:
    if service not in _circuit_breakers:
        _circuit_breakers[service] = pybreaker.CircuitBreaker(
            fail_max=5, reset_timeout=30, name=service
        )
    return _circuit_breakers[service]


async def _ms_with_circuit_breaker(
    service: str, callback: Callable[..., object]
) -> object:
    """Execute *callback* inside a circuit breaker.

    ``pybreaker``'s ``call_async`` relies on ``tornado.gen.coroutine`` which was
    removed in Python 3.14.  This wrapper replicates the state-machine logic
    (open guard, half-open transition, listener hooks, failure/success counting)
    using native ``async``/``await`` so no Tornado dependency is needed.
    """
    cb = _get_circuit_breaker(service)

    with cb._lock:
        # Pre-call: open-state guard raises CircuitBreakerError when the
        # reset timeout has not elapsed.  When the timeout *has* elapsed the
        # open state transitions to half-open and attempts a synchronous
        # ``self._breaker.call(func)``; we pass a no-op so that call
        # completes harmlessly — the real execution happens below.
        cb.state.before_call(lambda: None)
        for listener in cb.listeners:
            listener.before_call(cb, callback)

    try:
        result = await _await_if_needed(callback())
    except BaseException as exc:
        with cb._lock:
            cb.state._handle_error(exc)
        raise  # pragma: no cover — _handle_error(reraise=True) always re-raises
    else:
        with cb._lock:
            cb.state._handle_success()
        return result


def _ms_get_circuit_state(service: str) -> str:
    cb = _get_circuit_breaker(service)
    return cb.current_state


def _ms_reset_circuit(service: str) -> None:
    if service in _circuit_breakers:
        del _circuit_breakers[service]


async def _ms_with_retry(callback: Callable[..., object], max_retries: int) -> object:
    retrying = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(max_retries),
        wait=tenacity.wait_fixed(1),
        reraise=True,
    )

    async def _call() -> object:
        return await _await_if_needed(callback())

    return await retrying(_call)


async def _ms_with_exponential_backoff(
    callback: Callable[..., object], max_retries: int, backoff_ms: int
) -> object:
    retrying = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(max_retries),
        wait=tenacity.wait_exponential(multiplier=backoff_ms / 1000),
        reraise=True,
    )

    async def _call() -> object:
        return await _await_if_needed(callback())

    return await retrying(_call)


async def _ms_with_timeout(callback: Callable[..., object], timeout_ms: int) -> object:
    timeout_seconds = timeout_ms / 1000
    token = _microservice_http_timeout.set(timeout_seconds)
    try:
        return await asyncio.wait_for(
            _await_if_needed(callback()),
            timeout=timeout_seconds,
        )
    finally:
        _microservice_http_timeout.reset(token)


_bulkhead_semaphores: dict[str, asyncio.Semaphore] = {}


async def _ms_with_bulkhead(service: str, callback: Callable[..., object]) -> object:
    if service not in _bulkhead_semaphores:
        _bulkhead_semaphores[service] = asyncio.Semaphore(10)
    async with _bulkhead_semaphores[service]:
        return await _await_if_needed(callback())


# ── Tracing ──


def _ms_propagate_context(headers: dict) -> dict:
    tid = _trace_id.get()
    if not tid:
        tid = str(uuid.uuid4())
        _trace_id.set(tid)
    headers["X-Trace-Id"] = tid
    return headers


def _ms_get_trace_id() -> str:
    tid = _trace_id.get()
    if not tid:
        tid = str(uuid.uuid4())
        _trace_id.set(tid)
    return tid


def _ms_set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)


# ── Load balancing ──


def _ms_get_next_instance(service: str) -> str:
    """Round-robin instance selection."""
    return _resolve_service_url(service)


def _ms_get_all_instances(service: str) -> list[str]:
    """Get all instances (single instance per env-based discovery)."""
    return [_resolve_service_url(service)]


# ── Rate limiting ──

_rate_limit_counters: dict[str, list[float]] = {}


async def _ms_check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Check if request is within rate limit (in-memory)."""
    now = time.time()
    if key not in _rate_limit_counters:
        _rate_limit_counters[key] = []
    _rate_limit_counters[key] = [
        t for t in _rate_limit_counters[key] if now - t < window_seconds
    ]
    if len(_rate_limit_counters[key]) >= limit:
        return False
    _rate_limit_counters[key].append(now)
    return True


async def _ms_get_rate_limit_status(key: str) -> dict[str, object]:
    """Get rate limit status."""
    timestamps = _rate_limit_counters.get(key, [])
    return {
        "key": key,
        "count": len(timestamps),
        "oldest": min(timestamps) if timestamps else None,
    }
