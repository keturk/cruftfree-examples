"""Trusted-caller token for outbound peer calls. Auto-generated.

Acquires and caches (until shortly before expiry) this service's own trusted-caller
token for the system's trusted-caller audience, so every outbound cross-service
``uses`` request can attach it as ``X-CruftFree-Caller-Token``.
The token is the service's managed-identity access token for the audience's
``/.default`` scope.
"""

from __future__ import annotations

import asyncio
import logging
import time

from helpdesk_notice_service.config import _credentials
from helpdesk_notice_service.config.settings import get_settings

logger = logging.getLogger(__name__)

_EXPIRY_SKEW_SECONDS: float = 300.0
_lock = asyncio.Lock()
_cached_token: str = ""
_cached_expiry: float = 0.0

# The longest acquiring the token may take. It is bounded on its own: never charged
# against an outbound call's timeout, and never left unbounded.
_CREDENTIAL_ACQUIRE_TIMEOUT_SECONDS: float = 15.0


class CallerTokenTimeoutError(Exception):
    """The trusted-caller token was not obtained within its bound."""


async def acquire_caller_token() -> str:
    """Return a cached-until-expiry trusted-caller token for the audience.

    Returns:
        The BARE JWT to place on the ``X-CruftFree-Caller-Token`` header -- the raw
        token only, with no ``Bearer `` scheme prefix. That header is a custom
        header, not ``Authorization``, so RFC 6750's prefix does not apply to it;
        prefixing the value makes every consumer's JWT library fail to decode the
        header segment and reject the request.

    Raises:
        CallerTokenTimeoutError: When the token is not obtained within
            ``_CREDENTIAL_ACQUIRE_TIMEOUT_SECONDS``.
    """
    try:
        return await asyncio.wait_for(
            _cached_or_minted_token(), timeout=_CREDENTIAL_ACQUIRE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as exc:
        raise CallerTokenTimeoutError(
            "The trusted-caller token was not obtained within "
            f"{_CREDENTIAL_ACQUIRE_TIMEOUT_SECONDS}s. Expected the platform token "
            "endpoint to answer; check its reachability from this service."
        ) from exc


async def _cached_or_minted_token() -> str:
    """The cached token, or a freshly minted one; ``acquire_caller_token`` bounds it."""
    global _cached_token, _cached_expiry
    if _cached_token and time.time() < _cached_expiry - _EXPIRY_SKEW_SECONDS:
        return _cached_token
    async with _lock:
        if _cached_token and time.time() < _cached_expiry - _EXPIRY_SKEW_SECONDS:
            return _cached_token
        audience = get_settings().trusted_caller_audience
        credential = _credentials.azure_credential()
        token = await credential.get_token(f"{audience}/.default")
        _cached_token = token.token
        _cached_expiry = float(token.expires_on)
        logger.debug("caller_token_acquired expiry=%s", _cached_expiry)
        return _cached_token
