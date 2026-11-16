"""Trusted-caller token middleware. Auto-generated. Do not edit manually.

Validates the ``X-CruftFree-Caller-Token`` header (a JWT the managed gateway or a
calling peer service minted with its own platform identity) on every non-probe
route BEFORE the user-JWT layer.

A caller is trusted iff its token: is signed RS256 by a key
of the expected issuer (found through the issuer's OpenID discovery document,
fetched over verified TLS, which must name that same issuer), has ``iss`` == the
expected issuer, ``aud`` == the trusted-caller audience, and its
``sub`` claim in the per-service trusted-principal allowlist. No
network heuristics -- pure caller identity, identical under every ingress mode.

Emitted only on a platform whose managed gateway forwards a caller token AND for a
service something can call (``trusted_caller_inbound``). A service that only CALLS
peers emits no middleware -- it has no inbound request to validate, only
``_caller_token.py`` to mint its own.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import urllib.request

import jwt
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from cityservices_geocoder_mock.config.settings import get_settings
from cityservices_geocoder_mock.errors.problem_details import (
    problem_response,
    problem_title,
)

logger = logging.getLogger(__name__)

#: The problem families a refusal answers with, rendered from the registry.
_FAMILY_UNAUTHORIZED: str = "unauthorized"
_FAMILY_FORBIDDEN: str = "forbidden"

#: Log-only reason codes, rendered from the shared AuthReasonCode vocabulary.
_REASON_MISSING_TOKEN: str = "missing_token"
_REASON_MALFORMED_TOKEN: str = "malformed_token"
_REASON_EXPIRED_TOKEN: str = "expired_token"
_REASON_BAD_SIGNATURE: str = "bad_signature"
_REASON_ISSUER_MISMATCH: str = "issuer_mismatch"
_REASON_AUDIENCE_MISMATCH: str = "audience_mismatch"
_REASON_JWKS_REFRESH_FAILED: str = "jwks_refresh_failed"
_REASON_UNTRUSTED_CALLER: str = "untrusted_caller"

_CALLER_TOKEN_HEADER = "X-CruftFree-Caller-Token"
# The header's value is the BARE JWT -- this is a custom header, not
# ``Authorization``, so RFC 6750's scheme prefix does not belong on it. A prefixed
# value is stripped anyway (defence in depth): otherwise PyJWT tries to
# base64url-decode "Bearer eyJ..." as the header segment and rejects every request
# with "Invalid header padding" before any signature/issuer/audience check runs.
_CALLER_TOKEN_BEARER_PREFIX = "Bearer "
# App Service platform probes never transit APIM and carry no token. The set is
# rendered from context, not hardcoded: it always contains the SAME liveness
# route the Azure web-app module sets as its App Service healthCheckPath
# (LanguageRuntimeSpec.app_service_liveness_probe_path), so the platform probe is
# exempt by construction rather than by two templates agreeing on a literal by
# luck. The dependency-gated /health route (probed by the gateway and operators)
# is exempt too.
_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/live",
        "/health",
    }
)
_TOKEN_ALGORITHMS: tuple[str, ...] = ("RS256",)
#: The claim naming the calling principal, as the platform's issuer writes it.
_PRINCIPAL_CLAIM: str = "sub"
_DISCOVERY_PATH: str = "/.well-known/openid-configuration"
_HTTPS_SCHEME = "https://"
_FETCH_TIMEOUT_SECONDS = 5
_MAX_DISCOVERY_BYTES = 1_048_576

_jwks_client: PyJWKClient | None = None


class _DiscoveryError(Exception):
    """The issuer's discovery document could not be fetched or is not trustworthy."""


def _tls_context() -> ssl.SSLContext:
    """A certificate- and hostname-verifying TLS context (the library default)."""
    return ssl.create_default_context()


def _discover_jwks_uri(issuer: str) -> str:
    """Resolve the issuer's ``jwks_uri`` from its OpenID discovery document.

    Raises:
        _DiscoveryError: The issuer or the document is not served over HTTPS, the
            document is malformed, names a different issuer, or points at a
            non-HTTPS key set.
    """
    if not issuer.startswith(_HTTPS_SCHEME):
        raise _DiscoveryError("issuer is not an https URL")
    discovery_url = issuer.rstrip("/") + _DISCOVERY_PATH
    request = urllib.request.Request(
        discovery_url, headers={"Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_FETCH_TIMEOUT_SECONDS, context=_tls_context()
        ) as response:
            if not response.geturl().startswith(_HTTPS_SCHEME):
                raise _DiscoveryError("discovery document redirected off https")
            document = json.loads(response.read(_MAX_DISCOVERY_BYTES))
    except (OSError, ValueError) as exc:
        raise _DiscoveryError("discovery document unavailable") from exc
    if not isinstance(document, dict) or document.get("issuer") != issuer:
        raise _DiscoveryError("discovery document names a different issuer")
    jwks_uri = document.get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri.startswith(_HTTPS_SCHEME):
        raise _DiscoveryError("discovery document names no https key set")
    return jwks_uri


def _get_jwks_client(issuer: str) -> PyJWKClient:
    """Return the issuer's key-set client, discovered once per process."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            _discover_jwks_uri(issuer),
            cache_keys=True,
            timeout=_FETCH_TIMEOUT_SECONDS,
            ssl_context=_tls_context(),
        )
    return _jwks_client


def _verify(token: str, issuer: str, audience: str) -> dict[str, object]:
    """Verify *token*'s signature, issuer, audience and expiry; return its claims.

    Blocking (the first call fetches the discovery document and the key set), so
    the middleware runs it off the event loop.
    """
    signing_key = _get_jwks_client(issuer).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=list(_TOKEN_ALGORITHMS),
        audience=audience,
        issuer=issuer,
        options={"require": ["exp", "iss", "aud"]},
    )


def _parse_trusted_principals(raw: str) -> frozenset[str]:
    """Parse the comma-joined trusted principal-id app setting into a set."""
    return frozenset(p.strip() for p in raw.split(",") if p.strip())


def _bare_token(raw: str) -> str:
    """Return the bare JWT, tolerating an optional ``Bearer `` scheme prefix.

    The contract is a bare token, so this strip is a safety net rather than the
    expected path: it keeps a single non-conforming producer (e.g. a gateway policy
    that prefixes the value) from rejecting every request instead of none.
    """
    prefix = _CALLER_TOKEN_BEARER_PREFIX
    if raw[: len(prefix)].lower() == prefix.lower():
        return raw[len(prefix) :].strip()
    return raw


def _verification_failure_reason(exc: Exception) -> str:
    """Classify a failed caller-token verification into the shared vocabulary.

    The exception text is never the reason: it can carry issuer, audience or key
    detail. ``InvalidSignatureError`` is a ``DecodeError`` subclass, so it is
    tested first. Any other verification failure is a bad signature, the same
    terminal classification the user-token validator applies.
    """
    if isinstance(exc, (PyJWKClientError, _DiscoveryError)):
        return _REASON_JWKS_REFRESH_FAILED
    if isinstance(exc, ExpiredSignatureError):
        return _REASON_EXPIRED_TOKEN
    if isinstance(exc, InvalidSignatureError):
        return _REASON_BAD_SIGNATURE
    if isinstance(exc, InvalidAudienceError):
        return _REASON_AUDIENCE_MISMATCH
    if isinstance(exc, InvalidIssuerError):
        return _REASON_ISSUER_MISMATCH
    if isinstance(exc, DecodeError):
        return _REASON_MALFORMED_TOKEN
    return _REASON_BAD_SIGNATURE


def _refuse(request: Request, family: str, reason_code: str) -> Response:
    """Log the one refusal event and answer an opaque problem.

    The body is the family title only -- the client never learns which check
    failed (the reason code goes to the log, never to the response). The log
    carries the vocabulary reason code and the path: no exception text, no
    principal id, no token. This middleware runs outside the exception
    handlers, so it returns the same responder they call.
    """
    logger.warning(
        "identity.trusted_caller.rejected reason_code=%s path=%s",
        reason_code,
        request.url.path,
    )
    return problem_response(
        family, instance=request.url.path, detail=problem_title(family)
    )


class TrustedCallerMiddleware(BaseHTTPMiddleware):
    """Reject any non-probe request lacking a valid trusted-caller token."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """Validate the caller token before the request reaches the user-JWT layer."""
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)  # type: ignore[misc, operator]
        settings = get_settings()
        audience = settings.trusted_caller_audience
        issuer = settings.trusted_caller_issuer
        trusted = _parse_trusted_principals(settings.trusted_caller_principal_ids)
        token = _bare_token(request.headers.get(_CALLER_TOKEN_HEADER, ""))
        if not token:
            return _refuse(request, _FAMILY_UNAUTHORIZED, _REASON_MISSING_TOKEN)
        try:
            claims = await asyncio.to_thread(_verify, token, issuer, audience)
        except (InvalidTokenError, PyJWKClientError, _DiscoveryError) as exc:
            return _refuse(
                request, _FAMILY_UNAUTHORIZED, _verification_failure_reason(exc)
            )
        principal = claims.get(_PRINCIPAL_CLAIM)
        if not isinstance(principal, str) or principal not in trusted:
            return _refuse(request, _FAMILY_FORBIDDEN, _REASON_UNTRUSTED_CALLER)
        # Neither the principal nor the token is logged: the path alone identifies the call.
        logger.debug(
            "identity.service_principal.authenticated path=%s", request.url.path
        )
        # The one place a request is marked as having come through the verified gateway:
        # on this accept path only. The client-address resolver reads the gateway's
        # asserted header solely for a request carrying this mark. ``request.state`` is
        # shared per ASGI scope, so the inner application and the outer logging
        # middleware both see it.
        request.state.verified_trusted_caller = True
        return await call_next(request)  # type: ignore[misc, operator]
