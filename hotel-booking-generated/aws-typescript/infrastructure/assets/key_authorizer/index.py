"""Lambda REQUEST authorizer of the API gateway: edge credential decisions, and caller-token minting.

A REST API has no native JWT authorizer, so this authorizer decides every method
that checks a credential there. An HTTP API route carries exactly one authorizer, and
the native JWT authorizer rejects every request without a bearer token, so on an HTTP
API an endpoint whose contract also admits an API key, or that is ``auth(optional)``,
uses this one instead. On either API it guards every route forwarded to a service
that verifies a trusted-caller token, because only this authorizer can mint the token:
once a request is admitted, it returns a web identity token (STS
``GetWebIdentityToken``, signed for this function's own role and the application's
trusted-caller audience) in its context, and the route's integration overwrites the
caller-token header with it. A token is reused until shortly before it expires; a
failure to mint fails the request (the gateway answers 500), never forwards it without
a token.

Every endpoint has its own route (its method and path template), so the
route key the request arrived on (an HTTP API event's ``routeKey``; on a REST API
event, its method and ``resource``) names exactly one endpoint: the request's
normalized path is matched against that endpoint's own path pattern (the route's
``{param}`` template can be wider than the endpoint, for a segment with an
extension). No route key in the table, or a path matching no pattern, is denied.
Then:

- a ``required`` endpoint with no admitted key admits only an ``Authorization``
  bearer JWT validated exactly as the gateway's JWT authorizer validates one
  (RSA signature against the issuer's JWKS, discovered over verified TLS;
  ``iss``; ``aud`` or, only when ``aud`` is absent, ``client_id``; ``exp``;
  ``nbf``; ``iat``);
- a ``required`` key-admitting endpoint admits that bearer JWT, OR no
  ``Authorization`` header plus exactly one API-key header that endpoint admits,
  within the presented-key bounds (32-256 characters, printable ASCII 0x21-0x7E);
- an ``optional`` endpoint admits a request presenting no credential, and
  validates exactly as above any ``Authorization`` bearer it does present: a
  malformed, expired or otherwise invalid credential is denied, never skipped;
- a ``none`` endpoint (one that checks nothing at the edge, carried only for the
  minting) admits the request without reading any credential: the owning service
  remains the enforcement point, as on a gateway with no edge authorizer.

Every other combination -- both credentials, neither (on a ``required``
endpoint), two key headers, an unknown route or endpoint, a malformed path, or
any error while evaluating -- is denied. The owning service still verifies the
key itself; this function only gates presence and shape.

The path is normalized the way a backend resolves it before matching: an
encoded slash or any backslash (which backends disagree about) is denied, the
rest is percent-decoded once, one trailing ``/`` is dropped, and an empty,
``.`` or ``..`` segment is denied.

No identity sources and a zero result TTL, so it runs on every request and its
decision is never cached. It never logs a header value: only the decision and a
fixed reason string.
"""

from __future__ import annotations

import json
import logging
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections.abc import Mapping

import boto3
import jwt
from jwt import PyJWKClient, PyJWTError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#: The issuer the gateway's JWT authorizer is configured with; ``None`` when the
#: gateway declares no ``auth.jwt`` (then every endpoint is decided ``none``).
_ISSUER: str | None = 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_MarramIdentity'

#: The audience union a bearer must fall in: the declared audiences, and the
#: gateway-facing App Client ids the stack resolves from the identity stack's exports.
_AUDIENCES: frozenset[str] = frozenset(('marram-identity-app',)) | frozenset(
    os.environ['GATEWAY_CLIENT_AUDIENCES'].split(",")
)
#: The credential modes an endpoint is decided under.
_MODE_REQUIRED = 'required'
_MODE_OPTIONAL = 'optional'
_MODE_NONE = 'none'

#: Caller-token minting: the application's trusted-caller audience (``None`` when the
#: gateway forwards to no service that verifies one), the regional security token
#: service it is minted at, the lifetime requested (the role's grant allows no more)
#: and the signature algorithm the services verify.
_MINT_AUDIENCE: str | None = 'urn:cruftfree:trusted-caller:hotel-system'
_MINT_REGION: str | None = 'us-east-1'
_MINT_LIFETIME_SECONDS: int = 300
_MINT_ALGORITHM: str = 'RS256'
#: Renew a cached token once less than this much of its lifetime is left.
_MINT_RENEW_BEFORE_SECONDS: float = _MINT_LIFETIME_SECONDS / 5
#: The authorizer-context key the integrations read the token from.
_CALLER_TOKEN_CONTEXT_KEY: str = 'callerToken'

#: Route key (``<METHOD> <path template>``) -> the one endpoint behind that route, as
#: (anchored path pattern, credential mode, lower-cased API-key headers the
#: endpoint admits).
_ROUTE_ENDPOINTS: dict[str, tuple[str, str, tuple[str, ...]]] = {'DELETE /api/v1/desk/room_types/{p5}': ('^/api/v1/desk/room_types/[^/]+$', 'required', ()), 'GET /__cruftfree_openapi__/hotel-channel-mock': ('^/__cruftfree_openapi__/hotel\\-channel\\-mock$', 'required', ()), 'GET /__cruftfree_openapi__/hotel-email-mock': ('^/__cruftfree_openapi__/hotel\\-email\\-mock$', 'required', ()), 'GET /__cruftfree_openapi__/hotel-notice-service': ('^/__cruftfree_openapi__/hotel\\-notice\\-service$', 'required', ()), 'GET /__cruftfree_openapi__/hotel-payment-mock': ('^/__cruftfree_openapi__/hotel\\-payment\\-mock$', 'required', ()), 'GET /__cruftfree_openapi__/hotel-stay-service': ('^/__cruftfree_openapi__/hotel\\-stay\\-service$', 'required', ()), 'GET /api/v1/desk/arrivals': ('^/api/v1/desk/arrivals$', 'required', ()), 'GET /api/v1/desk/calendar': ('^/api/v1/desk/calendar$', 'required', ()), 'GET /api/v1/desk/channel/published_nights': ('^/api/v1/desk/channel/published_nights$', 'required', ()), 'GET /api/v1/desk/departures': ('^/api/v1/desk/departures$', 'required', ()), 'GET /api/v1/desk/email/outbounds': ('^/api/v1/desk/email/outbounds$', 'required', ()), 'GET /api/v1/desk/health': ('^/api/v1/desk/health$', 'none', ()), 'GET /api/v1/desk/notices': ('^/api/v1/desk/notices$', 'required', ()), 'GET /api/v1/desk/notices/health': ('^/api/v1/desk/notices/health$', 'none', ()), 'GET /api/v1/desk/occupancy': ('^/api/v1/desk/occupancy$', 'required', ()), 'GET /api/v1/desk/payment/card_charges': ('^/api/v1/desk/payment/card_charges$', 'required', ()), 'GET /api/v1/desk/room_types': ('^/api/v1/desk/room_types$', 'required', ()), 'GET /api/v1/desk/room_types/{p5}': ('^/api/v1/desk/room_types/[^/]+$', 'required', ()), 'GET /api/v1/desk/rooms': ('^/api/v1/desk/rooms$', 'required', ()), 'GET /api/v1/desk/stays': ('^/api/v1/desk/stays$', 'required', ()), 'GET /api/v1/desk/stays/{p5}': ('^/api/v1/desk/stays/[^/]+$', 'required', ()), 'GET /api/v1/desk/stays/{p5}/free-rooms': ('^/api/v1/desk/stays/[^/]+/free\\-rooms$', 'required', ()), 'GET /api/v1/desk/today': ('^/api/v1/desk/today$', 'required', ()), 'GET /api/v1/stays/mine': ('^/api/v1/stays/mine$', 'required', ()), 'GET /api/v1/stays/mine/{p5}': ('^/api/v1/stays/mine/[^/]+$', 'required', ()), 'GET /api/v1/stays/room-types': ('^/api/v1/stays/room\\-types$', 'none', ()), 'GET /api/v1/stays/room-types/{p5}': ('^/api/v1/stays/room\\-types/[^/]+$', 'none', ()), 'GET /v1/__cruftfree_gateway_health__/hotel-channel-mock': ('^/v1/__cruftfree_gateway_health__/hotel\\-channel\\-mock$', 'none', ()), 'GET /v1/__cruftfree_gateway_health__/hotel-email-mock': ('^/v1/__cruftfree_gateway_health__/hotel\\-email\\-mock$', 'none', ()), 'GET /v1/__cruftfree_gateway_health__/hotel-payment-mock': ('^/v1/__cruftfree_gateway_health__/hotel\\-payment\\-mock$', 'none', ()), 'POST /api/v1/desk/check-in': ('^/api/v1/desk/check\\-in$', 'required', ()), 'POST /api/v1/desk/note': ('^/api/v1/desk/note$', 'required', ()), 'POST /api/v1/desk/room_types': ('^/api/v1/desk/room_types$', 'required', ()), 'POST /api/v1/desk/rooms/{p5}/condition': ('^/api/v1/desk/rooms/[^/]+/condition$', 'required', ()), 'POST /api/v1/desk/stays/{p5}/cancel': ('^/api/v1/desk/stays/[^/]+/cancel$', 'required', ()), 'POST /api/v1/desk/stays/{p5}/check-out': ('^/api/v1/desk/stays/[^/]+/check\\-out$', 'required', ()), 'POST /api/v1/stays/hold': ('^/api/v1/stays/hold$', 'required', ()), 'POST /api/v1/stays/mine/{p5}/cancel': ('^/api/v1/stays/mine/[^/]+/cancel$', 'required', ()), 'POST /api/v1/stays/pay': ('^/api/v1/stays/pay$', 'required', ()), 'POST /api/v1/stays/search': ('^/api/v1/stays/search$', 'none', ()), 'POST /v1/availability': ('^/v1/availability$', 'required', ('x-channel-api-key',)), 'POST /v1/charges': ('^/v1/charges$', 'required', ('x-payment-api-key',)), 'POST /v1/deliveries': ('^/v1/deliveries$', 'required', ('x-email-api-key',)), 'POST /v1/refunds': ('^/v1/refunds$', 'required', ('x-payment-api-key',)), 'PUT /api/v1/desk/room_types/{p5}': ('^/api/v1/desk/room_types/[^/]+$', 'required', ())}

#: The same table with each path pattern compiled once per execution environment.
_ENDPOINT_MATCHERS: dict[str, tuple[re.Pattern[str], str, tuple[str, ...]]] = {
    route_key: (re.compile(pattern), mode, key_headers)
    for route_key, (pattern, mode, key_headers) in _ROUTE_ENDPOINTS.items()
}

#: Encoded path separators: backends disagree on whether they split on them.
_ENCODED_SEPARATORS: tuple[str, ...] = ("%2f", "%5c")
_REJECTED_SEGMENTS: frozenset[str] = frozenset({"", ".", ".."})

#: The HTTP API JWT authorizer accepts RSA-based signatures only.
_ALLOWED_ALGORITHMS: tuple[str, ...] = ("RS256", "RS384", "RS512")

_AUTHORIZATION_HEADER = "authorization"
_BEARER_PREFIX = "bearer "
_HTTPS_SCHEME = "https://"
_DISCOVERY_SUFFIX = "/.well-known/openid-configuration"
_FETCH_TIMEOUT_SECONDS = 5
_MAX_DISCOVERY_BYTES = 1_048_576

_KEY_MIN_LENGTH = 32
_KEY_MAX_LENGTH = 256
_KEY_MIN_CHAR = 0x21
_KEY_MAX_CHAR = 0x7E

#: One JWKS client per execution environment, built after a successful discovery.
_jwks_clients: dict[str, PyJWKClient] = {}

#: The caller token minted in this execution environment, and when it expires.
_minted_token: str = ""
_minted_expiry: float = 0.0
_sts_client: object | None = None


class _Denied(Exception):
    """Carries the fixed, value-free reason a request is denied."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _tls_context() -> ssl.SSLContext:
    """A certificate- and hostname-verifying TLS context (the library default)."""
    return ssl.create_default_context()


def _discover_jwks_uri() -> str:
    """Resolve the issuer's ``jwks_uri`` from its OpenID discovery document.

    Raises:
        _Denied: If the document is not served over HTTPS, is malformed, names a
            different issuer, or points at a non-HTTPS key set.
    """
    if _ISSUER is None:
        raise _Denied("no_issuer")
    discovery_url = _ISSUER.rstrip("/") + _DISCOVERY_SUFFIX
    request = urllib.request.Request(discovery_url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(
        request, timeout=_FETCH_TIMEOUT_SECONDS, context=_tls_context()
    ) as response:
        if not response.geturl().startswith(_HTTPS_SCHEME):
            raise _Denied("discovery_not_https")
        document = json.loads(response.read(_MAX_DISCOVERY_BYTES))
    if not isinstance(document, dict):
        raise _Denied("discovery_malformed")
    if "issuer" not in document or document["issuer"] != _ISSUER:
        raise _Denied("discovery_issuer_mismatch")
    if "jwks_uri" not in document:
        raise _Denied("discovery_malformed")
    jwks_uri = document["jwks_uri"]
    if not isinstance(jwks_uri, str) or not jwks_uri.startswith(_HTTPS_SCHEME):
        raise _Denied("jwks_uri_not_https")
    return jwks_uri


def _jwks_client() -> PyJWKClient:
    """The issuer's JWKS client, discovered once per execution environment."""
    if _ISSUER not in _jwks_clients:
        _jwks_clients[_ISSUER] = PyJWKClient(
            _discover_jwks_uri(),
            cache_keys=True,
            timeout=_FETCH_TIMEOUT_SECONDS,
            ssl_context=_tls_context(),
        )
    return _jwks_clients[_ISSUER]


def _audience_matches(claims: Mapping[str, object]) -> bool:
    """``aud`` must name a configured audience; ``client_id`` counts only without ``aud``."""
    if "aud" in claims:
        audience = claims["aud"]
        values = [audience] if isinstance(audience, str) else audience
        if not isinstance(values, list):
            return False
        return any(isinstance(value, str) and value in _AUDIENCES for value in values)
    if "client_id" in claims:
        client_id = claims["client_id"]
        return isinstance(client_id, str) and client_id in _AUDIENCES
    return False


def _issued_in_the_past(claims: Mapping[str, object]) -> bool:
    """``iat``, when present, must be a number no later than now."""
    if "iat" not in claims:
        return True
    issued_at = claims["iat"]
    if isinstance(issued_at, bool) or not isinstance(issued_at, (int, float)):
        return False
    return issued_at <= time.time()


def _bearer_token(authorization: str) -> str:
    """The token, with or without its ``Bearer`` prefix (as the JWT authorizer accepts)."""
    if authorization.lower().startswith(_BEARER_PREFIX):
        return authorization[len(_BEARER_PREFIX):].strip()
    return authorization.strip()


def _validate_bearer(authorization: str) -> None:
    """Validate the bearer JWT exactly as the gateway's JWT authorizer does.

    Raises:
        _Denied: If the token is missing, malformed, signed by an unknown key or
            a non-RSA algorithm, or fails any claim check.
    """
    token = _bearer_token(authorization)
    if not token:
        raise _Denied("invalid_bearer")
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(_ALLOWED_ALGORITHMS),
            issuer=_ISSUER,
            options={
                "require": ["exp", "iss"],
                "verify_aud": False,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_signature": True,
            },
        )
    except PyJWTError as exc:
        raise _Denied("invalid_bearer") from exc
    if not _audience_matches(claims) or not _issued_in_the_past(claims):
        raise _Denied("invalid_bearer")


def _presented_key_in_bounds(value: str) -> bool:
    """Length 32-256 and every character printable ASCII 0x21-0x7E."""
    if not _KEY_MIN_LENGTH <= len(value) <= _KEY_MAX_LENGTH:
        return False
    return all(_KEY_MIN_CHAR <= ord(char) <= _KEY_MAX_CHAR for char in value)


def _lowercased_headers(event: Mapping[str, object]) -> dict[str, str]:
    """The request headers keyed by lower-cased name (an absent map is no headers)."""
    if "headers" not in event or event["headers"] is None:
        return {}
    raw = event["headers"]
    if not isinstance(raw, dict):
        raise _Denied("malformed_event")
    return {str(name).lower(): str(value) for name, value in raw.items()}


def _event_field(event: Mapping[str, object], name: str) -> object:
    """The event's field *name*; ``None`` when the event carries none."""
    return event[name] if name in event else None


def _request_path(raw: object) -> str:
    """The request path, normalized the way a backend resolves it.

    Raises:
        _Denied: If the path is absent, not absolute, carries an encoded or
            literal backslash or an encoded slash, is not valid UTF-8 once
            decoded, or has an empty, ``.`` or ``..`` segment.
    """
    if not isinstance(raw, str) or not raw.startswith("/") or "\\" in raw:
        raise _Denied("malformed_path")
    lowered = raw.lower()
    if any(separator in lowered for separator in _ENCODED_SEPARATORS):
        raise _Denied("malformed_path")
    try:
        decoded = urllib.parse.unquote(raw, errors="strict")
    except UnicodeDecodeError as exc:
        raise _Denied("malformed_path") from exc
    if decoded == "/":
        return decoded
    segments = decoded.split("/")[1:]
    if segments[-1] == "":
        segments = segments[:-1]
    if any(segment in _REJECTED_SEGMENTS for segment in segments):
        raise _Denied("malformed_path")
    return "/" + "/".join(segments)


def _matched_endpoint(route_key: object, raw_path: object) -> tuple[str, tuple[str, ...]]:
    """``(credential mode, admitted key headers)`` of the endpoint addressed.

    Raises:
        _Denied: If the route key is unknown, or the request path matches no
            pattern of the endpoint behind that route.
    """
    if not isinstance(route_key, str) or route_key not in _ENDPOINT_MATCHERS:
        raise _Denied("unknown_route")
    pattern, mode, key_headers = _ENDPOINT_MATCHERS[route_key]
    if not pattern.fullmatch(_request_path(raw_path)):
        raise _Denied("unknown_endpoint")
    return mode, key_headers


def _decide(route_key: object, raw_path: object, event: Mapping[str, object]) -> str:
    """Return the allow reason, or raise :class:`_Denied` with the deny reason."""
    mode, admitted = _matched_endpoint(route_key, raw_path)
    if mode == _MODE_NONE:
        return "unchecked"
    headers = _lowercased_headers(event)
    present_keys = [header for header in admitted if headers.get(header, "")]
    has_authorization = _AUTHORIZATION_HEADER in headers
    if has_authorization and present_keys:
        raise _Denied("ambiguous_credentials")
    if has_authorization:
        _validate_bearer(headers[_AUTHORIZATION_HEADER])
        return "bearer"
    if not present_keys:
        if mode == _MODE_OPTIONAL:
            return "anonymous"
        raise _Denied("no_credentials")
    if len(present_keys) > 1:
        raise _Denied("ambiguous_credentials")
    if not _presented_key_in_bounds(headers[present_keys[0]]):
        raise _Denied("key_out_of_bounds")
    return "key_present"


def _caller_token() -> str:
    """This function's trusted-caller token, minted (or reused until near expiry).

    Raises:
        RuntimeError: The gateway mints no token here, or the security token service
            returned none. Any SDK error propagates: the request fails, never forwards
            without a token.
    """
    global _minted_token, _minted_expiry, _sts_client
    if _MINT_AUDIENCE is None or _MINT_REGION is None:
        raise RuntimeError("this gateway forwards to no service that verifies a caller token")
    if _minted_token and time.time() < _minted_expiry - _MINT_RENEW_BEFORE_SECONDS:
        return _minted_token
    if _sts_client is None:
        _sts_client = boto3.client("sts", region_name=_MINT_REGION)
    response = _sts_client.get_web_identity_token(  # type: ignore[attr-defined]
        Audience=[_MINT_AUDIENCE],
        SigningAlgorithm=_MINT_ALGORITHM,
        DurationSeconds=_MINT_LIFETIME_SECONDS,
    )
    token = response["WebIdentityToken"]
    if not isinstance(token, str) or not token:
        raise RuntimeError("the security token service returned no web identity token")
    _minted_token = token
    _minted_expiry = response["Expiration"].timestamp()
    logger.info("caller_token_minted")
    return _minted_token


def _minted_context() -> dict[str, str]:
    """The authorizer context carrying the caller token, when the gateway mints."""
    if _MINT_AUDIENCE is None:
        return {}
    try:
        return {_CALLER_TOKEN_CONTEXT_KEY: _caller_token()}
    except Exception as exc:
        # Never forward without the token: the failure propagates and the gateway
        # answers 500. The error type alone is logged -- never a token.
        logger.error("caller_token_mint_failed error_type=%s", type(exc).__name__)
        raise


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    """API Gateway HTTP API REQUEST authorizer entry point (simple response)."""
    del context
    try:
        reason = _decide(_event_field(event, "routeKey"), _event_field(event, "rawPath"), event)
    except _Denied as denied:
        logger.info("authorizer_deny reason=%s", denied.reason)
        return {"isAuthorized": False}
    except Exception as exc:  # noqa: BLE001 -- any evaluation failure denies (fail closed)
        logger.warning("authorizer_deny reason=evaluation_error error_type=%s", type(exc).__name__)
        return {"isAuthorized": False}
    logger.info("authorizer_allow reason=%s", reason)
    minted = _minted_context()
    if not minted:
        return {"isAuthorized": True}
    return {"isAuthorized": True, "context": minted}


def _rest_route_key(event: Mapping[str, object]) -> str | None:
    """The table key of a REST request: its method and the resource path it matched.

    A REST event carries no route key of its own; ``resource`` is the path template the
    method was created under, as the table spells it.
    """
    method = _event_field(event, "httpMethod")
    resource = _event_field(event, "resource")
    if not isinstance(method, str) or not isinstance(resource, str):
        return None
    return f"{method} {resource}"


def rest_handler(event: dict[str, object], context: object) -> dict[str, object]:
    """API Gateway REST API REQUEST authorizer entry point (an IAM policy).

    Decides the request as :func:`handler` does and, once it is admitted, allows exactly
    the method it arrived on. A refused request raises ``Unauthorized``, which API
    Gateway answers with 401; so does any failure while deciding (fail closed).
    """
    del context
    method_arn = _event_field(event, "methodArn")
    if not isinstance(method_arn, str) or not method_arn:
        logger.info("authorizer_deny reason=malformed_event")
        raise RuntimeError("Unauthorized")
    try:
        reason = _decide(_rest_route_key(event), _event_field(event, "path"), event)
    except _Denied as denied:
        logger.info("authorizer_deny reason=%s", denied.reason)
        raise RuntimeError("Unauthorized") from None
    except Exception as exc:  # noqa: BLE001 -- any evaluation failure denies (fail closed)
        logger.warning("authorizer_deny reason=evaluation_error error_type=%s", type(exc).__name__)
        raise RuntimeError("Unauthorized") from None
    logger.info("authorizer_allow reason=%s", reason)
    minted = _minted_context()
    return {
        "principalId": "gateway",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": method_arn}
            ],
        },
        "context": minted,
    }
