"""Trusted-caller token for outbound peer calls. Auto-generated.

Acquires and caches (until shortly before expiry) this service's own trusted-caller
token for the system's trusted-caller audience, so every outbound cross-service
``uses`` request can attach it as ``X-CruftFree-Caller-Token``.
The token is a web identity token the platform's security token service signs for
the service's own role, with the audience as its ``aud`` claim.
"""

from __future__ import annotations

import asyncio
import logging
import time

from cityservices_request_service.config import _credentials
from cityservices_request_service.config.settings import get_settings

logger = logging.getLogger(__name__)

#: The lifetime requested for each token (the platform grant caps it at this value).
_TOKEN_LIFETIME_SECONDS: int = 300
#: Renew a token once less than this much of its lifetime is left.
_EXPIRY_SKEW_SECONDS: float = 60.0
_SIGNING_ALGORITHM: str = "RS256"
_lock = asyncio.Lock()
_cached_token: str = ""
_cached_expiry: float = 0.0

# The longest acquiring the token may take. It is bounded on its own: never charged
# against an outbound call's timeout, and never left unbounded.
_CREDENTIAL_ACQUIRE_TIMEOUT_SECONDS: float = 15.0


class CallerTokenTimeoutError(Exception):
    """The trusted-caller token was not obtained within its bound."""


def _mint_web_identity_token(audience: str) -> tuple[str, float]:
    """Ask the security token service for a token naming this service's role.

    Blocking (one SDK call), so :func:`acquire_caller_token` runs it off the event loop.

    Returns:
        ``(token, expiry as a POSIX timestamp)``.
    """
    sts = _credentials.aws_client("sts")
    response = sts.get_web_identity_token(
        Audience=[audience],
        SigningAlgorithm=_SIGNING_ALGORITHM,
        DurationSeconds=_TOKEN_LIFETIME_SECONDS,
    )
    return response["WebIdentityToken"], response["Expiration"].timestamp()


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
        _cached_token, _cached_expiry = await asyncio.to_thread(
            _mint_web_identity_token, audience
        )
        logger.debug("caller_token_acquired expiry=%s", _cached_expiry)
        return _cached_token
