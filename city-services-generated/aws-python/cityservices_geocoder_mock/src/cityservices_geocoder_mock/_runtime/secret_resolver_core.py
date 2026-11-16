"""Secret resolution by logical handle, the logic every generated secrets resolver binds.

Emitted verbatim as ``<package>/_runtime/secret_resolver_core.py``. The service's
``config/_secrets_resolver.py`` binds it to the service's generated secret
manifest, the fetch of the backend baked at generation time, and the cache
policy baked from ``SecretBackendPolicy``. Nothing here reads the environment,
holds a secret value, or defaults one.

Each handle is cached with a per-handle TTL (from the manifest, falling back to
the bound default) measured on a MONOTONIC clock. A long-lived process that
caches a secret forever never sees a rotation; a per-handle TTL plus lazy
refresh makes a rotated secret propagate within the TTL the next time the handle
is requested, **provided the backend is reachable**. On a refresh that fails
while a prior value is cached, the resolver serves the stale value and warns
(rotation is best-effort, availability is preserved) UNLESS fail-closed refresh
is bound, in which case the stale value is rejected. A handle with no prior
cached value and a failed/absent fetch always raises (the fail-closed
initial-miss contract). ``invalidate_secret`` is the single pre-TTL eviction
path, used by credential-aware wrappers to force one early refetch; it is
throttled per handle and never loops.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable, Mapping

logger = logging.getLogger(__name__)

#: A backend read: the value the backend stores for a handle, or ``None`` when it holds none.
SecretFetch = Callable[[str], Awaitable[str | None]]

#: Manifest entry field holding the backend-specific name, path or file leaf.
_RENDERED_NAME_KEY = "rendered_name"

#: Manifest entry field holding the handle's cache TTL in seconds (``0``: never expires).
_TTL_SECONDS_KEY = "ttl_seconds"

#: Manifest entry field holding the URL of the store that holds the handle.
_STORE_ENDPOINT_KEY = "store_endpoint"


class SecretReferences:
    """The service's secret manifest, read by logical handle.

    The resolver never derives a backend name: every derivation happened once,
    at generation time, in ``SecretReferenceManifest``.

    Args:
        references: ``SECRET_REFERENCES`` of the generated ``config._secret_manifest``:
            each declared handle mapped to its ``rendered_name``, ``ttl_seconds`` and
            ``store_endpoint``. Read on every lookup, never copied.
    """

    def __init__(self, references: Mapping[str, Mapping[str, object]]) -> None:
        self._references = references

    def _entry(self, handle: str) -> Mapping[str, object]:
        """The manifest entry of *handle*.

        Raises:
            KeyError: *handle* is not declared; the message names logical handles only.
        """
        entry = self._references.get(handle)
        if entry is None:
            raise KeyError(
                "Secret handle %r is not declared in the generated _secret_manifest. "
                "Declared handles: %s. "
                "This is a code-generation error — regenerate the service so the "
                "resolver and manifest are built from the same service definition."
                % (handle, sorted(self._references.keys()))
            )
        return entry

    def rendered_name(self, handle: str) -> str:
        """The backend-specific secret name, path, or leaf filename of *handle*.

        Raises:
            KeyError: *handle* is not declared in the manifest.
        """
        return str(self._entry(handle)[_RENDERED_NAME_KEY])

    def store_endpoint(self, handle: str) -> str:
        """The URL of the store holding *handle*.

        Each secret lives in the store the application placement gave it: the
        service's own store for a secret only this service reads, the application
        store for a shared one. Generation refused to emit a resolver for a backend
        that needs this unless every entry carries one.

        Raises:
            KeyError: *handle* is not declared in the manifest.
        """
        return str(self._entry(handle)[_STORE_ENDPOINT_KEY])

    def ttl_seconds(self, handle: str, default_seconds: int) -> int:
        """The cache TTL of *handle*: its manifest ``ttl_seconds``, else *default_seconds*.

        Raises:
            TypeError: The manifest entry's ``ttl_seconds`` is not an integer.
        """
        entry = self._references.get(handle)
        if entry is None or _TTL_SECONDS_KEY not in entry:
            return default_seconds
        ttl = entry[_TTL_SECONDS_KEY]
        if not isinstance(ttl, int):
            raise TypeError(
                "Secret handle %r has a manifest ttl_seconds of type %s; expected an "
                "integer number of seconds (0 for no expiry). Regenerate the service so "
                "the manifest is rebuilt." % (handle, type(ttl).__name__)
            )
        return ttl


class SecretResolver:
    """Resolves required secrets by logical handle with TTL-bounded caching.

    Args:
        backend: The secret backend baked at generation time, named in log lines
            and errors.
        references: The service's secret manifest.
        fetch: Reads one handle from the backend.
        default_ttl_seconds: The TTL of a handle whose manifest entry carries none;
            ``0`` means no expiry.
        fail_closed_on_refresh: When true, a failed refresh is fatal even with a
            prior value cached; when false, the stale value is served with a warning.
        invalidation_throttle_seconds: The minimum interval between two early
            evictions of one handle.
        clock: The MONOTONIC time source, in seconds.
    """

    def __init__(
        self,
        *,
        backend: str,
        references: SecretReferences,
        fetch: SecretFetch,
        default_ttl_seconds: int,
        fail_closed_on_refresh: bool,
        invalidation_throttle_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend = backend
        self._references = references
        self._fetch = fetch
        self._default_ttl_seconds = default_ttl_seconds
        self._fail_closed_on_refresh = fail_closed_on_refresh
        self._invalidation_throttle_seconds = invalidation_throttle_seconds
        self._clock = clock
        # handle -> (value, expires_at on the monotonic clock); served while clock() < expires_at.
        self._cache: dict[str, tuple[str, float]] = {}
        # Per-handle single-flight locks: concurrent refreshes of one handle collapse
        # to one backend read; different handles refresh concurrently.
        self._refresh_locks: dict[str, asyncio.Lock] = {}
        self._last_invalidated_at: dict[str, float] = {}

    def _refresh_lock_for(self, handle: str) -> asyncio.Lock:
        """The process-local single-flight lock of *handle*."""
        lock = self._refresh_locks.get(handle)
        if lock is None:
            lock = asyncio.Lock()
            self._refresh_locks[handle] = lock
        return lock

    def _unexpired(self, handle: str) -> str | None:
        """The cached value of *handle* while it is unexpired, else ``None``."""
        cached = self._cache.get(handle)
        if cached is not None and self._clock() < cached[1]:
            return cached[0]
        return None

    def _store(self, handle: str, value: str) -> None:
        """Cache *value* for *handle* until its TTL expires; a TTL of 0 never expires."""
        ttl = self._references.ttl_seconds(handle, self._default_ttl_seconds)
        expires_at = math.inf if ttl == 0 else self._clock() + ttl
        self._cache[handle] = (value, expires_at)

    async def get_secret(self, handle: str) -> str:
        """Resolve a required secret by logical handle.

        A cached value is returned while it is unexpired. On expiry the backend is
        re-read so a rotated secret propagates. Concurrent expired or missing reads
        of one handle collapse to a single backend fetch. If the re-read fails and a
        prior value is cached, the prior value is served with a warning unless
        fail-closed refresh is bound. An initial miss (no prior value, the fetch
        returns an absent or blank value) always raises. A blank value (empty or
        whitespace only, e.g. an empty mounted secret file) is treated exactly like
        an absent one: a keyed hash or comparison under an empty secret is forgeable
        by any caller.

        Returns:
            The resolved secret value. Never empty, never whitespace only.

        Raises:
            RuntimeError: The secret is absent or blank in the backend on an initial
                miss, or the backend cannot be reached and either no prior value is
                cached or fail-closed refresh is bound. The message names the
                handle, never the value.
            KeyError: The handle is not declared in the manifest.
        """
        unexpired = self._unexpired(handle)
        if unexpired is not None:
            return unexpired
        prior = self._cache.get(handle)
        async with self._refresh_lock_for(handle):
            refreshed = self._unexpired(handle)
            if refreshed is not None:
                return refreshed
            return await self._refresh(handle, prior)

    async def _refresh(self, handle: str, prior: tuple[str, float] | None) -> str:
        """Fetch *handle* from the backend, cache it, and return it (see :meth:`get_secret`)."""
        try:
            fetched = await self._fetch(handle)
        except Exception as exc:  # backend unreachable / SDK error on refresh
            if prior is not None and not self._fail_closed_on_refresh:
                logger.warning(
                    "secret_refresh_failed_serving_stale backend=%s handle=%s error=%s",
                    self._backend,
                    handle,
                    exc,
                )
                return prior[0]
            raise
        if fetched is not None:
            logger.debug("secret_fetched backend=%s handle=%s", self._backend, handle)
        if fetched is None or not fetched.strip():
            if prior is not None and not self._fail_closed_on_refresh:
                logger.warning(
                    "secret_refresh_absent_serving_stale backend=%s handle=%s",
                    self._backend,
                    handle,
                )
                return prior[0]
            # "not found" is the phrase the generated runtime-readiness probe
            # classifies as MISSING (every other RuntimeError is a backend ERROR);
            # a blank value is reported under the same phrase because it is
            # exactly as unusable as an absent one.
            raise RuntimeError(
                "Required secret %r not found in backend %r (absent or blank). "
                "Ensure a non-blank secret is provisioned in the deployment "
                "environment with the rendered name %r."
                % (handle, self._backend, self._references.rendered_name(handle))
            )
        self._store(handle, fetched)
        logger.info("secret_resolved backend=%s handle=%s", self._backend, handle)
        return fetched

    def invalidate_secret(self, handle: str, reason: str) -> None:
        """Evict *handle* so the next :meth:`get_secret` refetches it.

        For generated credential-aware wrappers ONLY: a wrapper that classifies a
        downstream error as a DEFINITIVE credential failure (e.g. an
        authentication-rejected response) calls this to drop the stale credential
        BEFORE its TTL expires, then retries the original operation at most once.
        A non-credential / transient error MUST NOT call this.

        The eviction is idempotent and throttled per handle; the subsequent
        :meth:`get_secret` is the single refetch and is protected by the per-handle
        single-flight lock. This never loops and never retries on its own.

        Args:
            handle: Logical secret handle to evict.
            reason: Short, value-free classification string for the log line.
        """
        now = self._clock()
        previous = self._last_invalidated_at.get(handle)
        if (
            previous is not None
            and now - previous < self._invalidation_throttle_seconds
        ):
            logger.warning(
                "secret_invalidation_throttled backend=%s handle=%s reason=%s",
                self._backend,
                handle,
                reason,
            )
            return
        self._last_invalidated_at[handle] = now
        if handle in self._cache:
            del self._cache[handle]
            logger.warning(
                "secret_invalidated backend=%s handle=%s reason=%s",
                self._backend,
                handle,
                reason,
            )

    def clear(self) -> None:
        """Forget every cached value, single-flight lock and invalidation time."""
        self._cache.clear()
        self._refresh_locks.clear()
        self._last_invalidated_at.clear()
