"""JWT authentication dependencies.

Binds the verified-principal core (``_runtime/auth_principal``) and adds the
credential chain and the route guards on top of it.

Provider: portalder
Algorithm allow-list: from identity provider plan.
"""

from __future__ import annotations

import contextvars
import logging
from collections.abc import Awaitable, Callable, Sequence

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import HTTPConnection

from cityservices_facility_service._runtime.auth_principal import (
    ClaimsProxy as _ClaimsProxy,
)
from cityservices_facility_service._runtime.auth_principal import PrincipalClaims
from cityservices_facility_service._runtime.auth_principal import (
    bind_current_user_id as bind_current_user_id,
)
from cityservices_facility_service._runtime.auth_principal import (
    current_user_id_ctx as _current_user_id_ctx,
)
from cityservices_facility_service._runtime.auth_principal import (
    current_user_subject_ctx as _current_user_subject_ctx,
)
from cityservices_facility_service._runtime.auth_principal import (
    forbidden as _forbidden,
)
from cityservices_facility_service._runtime.auth_principal import (
    get_current_user_id as get_current_user_id,
)
from cityservices_facility_service._runtime.auth_principal import (
    get_current_user_subject as get_current_user_subject,
)
from cityservices_facility_service._runtime.auth_principal import (
    role_value as _role_value,
)
from cityservices_facility_service._runtime.auth_principal import security as security
from cityservices_facility_service._runtime.auth_principal import (
    unauthorized as _unauthorized,
)
from cityservices_facility_service.identity import (
    JwksValidationError,
    declared_identity,
    load_provider_plan,
    local_user_id,
    resolve_provider_name,
    validate_token_claims,
)

logger = logging.getLogger(__name__)


class UserClaims(PrincipalClaims):
    """The verified principal; ``Auth.token()`` reads through the credential chain below."""

    __slots__ = ()

    def bearer_token(self) -> str:
        """This principal's bearer token (``Auth.token()``); denied when it holds none."""
        return require_token(self)


#: Log-only reason code for a provider plan that cannot be loaded or applied.
_REASON_PROVIDER_CONFIG_ERROR: str = "provider_config_error"


class AuthenticationFailed(Exception):
    """A credential that could not be verified (HTTP 401 / close 4401).

    Attributes:
        reason_code: The failure's reason code; logged, never returned to a caller.
    """

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code: str = reason_code


class AuthorizationDenied(Exception):
    """A verified principal the contract refuses (HTTP 403 / close 4403).

    Attributes:
        reason_code: The denial's reason code; logged, never returned to a caller.
    """

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code: str = reason_code


#: The verified principal of the request being served. ``authenticate_token``
#: binds it for the whole call path, so code outside a route handler's scope --
#: a service ``fn``, a rest_api ``fn``, an entity method, an entity lifecycle
#: hook -- reads ``Auth.*`` through the readers below instead of a
#: handler-bound ``current_user`` it does not have.
_current_principal_ctx: contextvars.ContextVar[UserClaims | None] = (
    contextvars.ContextVar("current_principal", default=None)
)


def require_current_user(reader: str) -> UserClaims:
    """The verified principal of the active request, for the ``Auth`` member *reader*.

    Fails closed: an anonymous request, an unguarded public route, or a call path with
    no request at all (a job, a consumer, startup) carries no principal, and
    the read of *reader* (``Auth.user``, ``Auth.token``, ``Auth.subject``,
    ``Auth.profile`` or ``Auth.identity``) is refused rather than answered
    with nothing. The 401 body is opaque; the member is logged server-side.

    Raises:
        HTTPException: 401 when no verified principal is bound.
    """
    principal = _current_principal_ctx.get()
    if principal is None:
        logger.warning("identity_principal_unbound reader=%s", reader)
        raise _unauthorized("Not authenticated")
    return principal


def current_user_has_role(role: object) -> bool:
    """Whether the active request's verified principal holds *role* (``Auth.hasRole``).

    The same exact, case-sensitive comparison a route handler's ``Auth.hasRole``
    and the route guard's role check make. ``False`` when no principal is bound
    (outside a request, an anonymous request, an unguarded public route): ``Auth.hasRole``
    never raises.
    """
    principal = _current_principal_ctx.get()
    if principal is None:
        return False
    return principal.has_role(role)


#: Log-only reason code for a principal that holds no bearer token to forward.
_REASON_NO_BEARER_TOKEN: str = "no_bearer_token"


def require_token(user: UserClaims) -> str:
    """The verified principal's own bearer token, or a denial when it holds none.

    A principal authenticated by a presented API key is issued no bearer
    token -- its ``token`` is the empty string, because forwarding the raw key
    is exactly what the key resolver never does. ``Auth.token()`` reads the
    token through here (``UserClaims.bearer_token``), so such a request is
    refused (403) rather than handed an empty string a caller could mistake
    for "no token needed".

    Raises:
        AuthorizationDenied: When the principal holds no bearer token.
    """
    if not user.token:
        raise AuthorizationDenied(_REASON_NO_BEARER_TOKEN)
    return user.token


def _bind_current_principal(
    principal: UserClaims, request: HTTPConnection | None
) -> None:
    """Bind a verified *principal* to the request being served.

    The one place a verified principal -- bearer-token or API-key -- reaches
    the three user-id surfaces and the ambient principal:
      1. ``_current_user_id_ctx`` (``get_current_user_id()`` -- model trait hooks)
      2. ``request.state.user_id`` (``Request.userId()`` -- handler DSL)
      3. ``UserClaims.profile_id`` / ``UserClaims.id`` (``Auth.userId()``)
    plus ``_current_user_subject_ctx`` (the raw subject) and
    ``_current_principal_ctx`` (:func:`require_current_user`).

    ``request.state.principal`` carries the verified ``UserClaims`` itself. It is
    the only channel the plan rate limiter and the GraphQL context read, and
    this is its only writer: callers reach here after every verification step.
    """
    _current_user_id_ctx.set(principal.profile_id)
    _current_user_subject_ctx.set(principal.subject or None)
    if request is not None:
        request.state.user_id = principal.profile_id
        request.state.principal = principal
    _current_principal_ctx.set(principal)


def _claims_expiry(claims: dict[str, object]) -> float | None:
    """The verified ``exp`` claim as epoch seconds, or ``None`` when absent or not numeric."""
    raw_exp = claims.get("exp")
    if isinstance(raw_exp, bool) or not isinstance(raw_exp, (int, float)):
        return None
    return float(raw_exp)


async def authenticate_token(token: str, request: HTTPConnection | None) -> UserClaims:
    """Verify *token* and resolve the application principal.

    Every step the bearer chain runs after the credential is extracted: JWKS
    validation against the identity provider plan (signature, expiry, issuer,
    audience, algorithm), attribution to the true provider by issuer AND
    audience, the local-identity resolution -- including the projected-mode
    profile lookup -- and the app-owned identity write-back. The REST
    dependencies below and every websocket_api / GraphQL subscription
    handshake call this one function; nothing re-implements it.

    When ``request`` is supplied (an HTTP request or a WebSocket), its
    ``state.user_id`` is overwritten with the resolved local id so that
    Request.userId() in handler DSL code sees the projected profile id, not the
    raw provider sub, and its ``state.principal`` is set to the verified
    ``UserClaims`` for the rate limiter and the GraphQL context.

    Raises:
        AuthenticationFailed: The token is invalid, expired or unverifiable, or
            the provider plan cannot be applied.
        AuthorizationDenied: A projected-mode principal whose profile cannot be
            resolved.
    """
    try:
        claims = await validate_token_claims(token)
    except JwksValidationError as exc:
        raise AuthenticationFailed(exc.reason_code) from exc
    except (RuntimeError, OSError, ValueError) as exc:
        logger.error(
            "identity_auth_config_error reason_code=%s error=%r",
            _REASON_PROVIDER_CONFIG_ERROR,
            exc,
        )
        raise AuthenticationFailed(_REASON_PROVIDER_CONFIG_ERROR) from exc
    sub = str(claims.get("sub", ""))
    plan_raw = claims.get("plan")
    if plan_raw is None:
        plan_raw = claims.get("planId")
    if plan_raw is None:
        plan_raw = claims.get("plan_id")
    plan = str(plan_raw).strip() if plan_raw is not None else ""
    raw_roles = claims.get("roles", [])
    roles: list[str] = (
        [str(r) for r in raw_roles] if isinstance(raw_roles, list) else []
    )
    # Attribute the verified token to its true provider by issuer AND audience
    # (the same selection the validator used) so the provider allow-list
    # (check_providers) can distinguish providers that share one IdP instance --
    # e.g. workforce vs customer on a single Zitadel server.
    provider = resolve_provider_name(claims) or ""
    # resolved_id is the single user id for all application-layer surfaces
    # (Auth.userId(), Request.userId(), get_current_user_id()). NEVER default to
    # the raw sub (a non-UUID subject in a UUID column causes runtime errors).
    # local_user_id() raises for projected-mode providers -- it is not called for
    # them; their resolved_id is the projected profile id below.
    resolved_id: str | None = None
    _profile_doc: dict[str, object] | None = None
    resolved_id = local_user_id(provider, sub) if sub else None
    principal = UserClaims(
        sub=sub,
        roles=roles,
        token=token,
        plan=plan,
        provider=provider,
        profile_id=resolved_id,
        profile=_profile_doc,
        identity=declared_identity(claims, provider),
        claims=claims,
        expires_at=_claims_expiry(claims),
        tenant_id=None,
    )
    # The resolved local id -- never the raw provider subject -- is the user id
    # every application-layer surface reads; the raw subject stays on .subject.
    _bind_current_principal(principal, request)
    return principal


def check_providers(user: UserClaims, allowed: Sequence[str]) -> None:
    """Deny a principal whose provider is not in *allowed*.

    The token has already been attributed to its true provider (issuer AND
    audience). A genuine token whose provider is not allowed is an
    authorization denial, never a validation failure.

    Raises:
        AuthorizationDenied: With the provider-not-allowed reason code.
    """
    if user.provider not in allowed:
        raise AuthorizationDenied("provider_not_allowed")


def check_roles(user: UserClaims, required: Sequence[object]) -> None:
    """Deny a principal holding none of *required* (flat any-of, no hierarchy).

    Raises:
        AuthorizationDenied: With the role-denied reason code.
    """
    required_values = [_role_value(r) for r in required]
    user_roles = [_role_value(r) for r in user.roles]
    if not any(role in user_roles for role in required_values):
        raise AuthorizationDenied("role_denied")


def check_principal_types(user: UserClaims, allowed: Sequence[str]) -> None:
    """Deny a principal whose provider's declared principal type is not in *allowed*.

    The principal type is the provider's ``principalType`` in the identity
    provider plan. A provider the plan does not declare, or one without a
    principal type, is denied (fail closed).

    Raises:
        AuthorizationDenied: With the principal-type-mismatch reason code.
    """
    providers = load_provider_plan().get("providers")
    entry = providers.get(user.provider) if isinstance(providers, dict) else None
    principal_type = entry.get("principalType") if isinstance(entry, dict) else None
    if not isinstance(principal_type, str) or principal_type not in allowed:
        raise AuthorizationDenied("principal_type_mismatch")


class OptionalCaller:
    """The caller of an ``auth(optional)`` route: a verified principal, or anonymous.

    ``Auth.user()`` is nullable (``user()`` returns ``None`` for an anonymous
    request). ``Auth.userId()``, ``Auth.token()``, ``.subject``, ``.profile``
    and ``.identity`` on an anonymous request raise the unauthenticated error
    (the opaque 401); ``Auth.hasRole`` reads ``roles``, which is empty.
    """

    __slots__ = ("_claims",)

    def __init__(self, claims: UserClaims | None) -> None:
        self._claims: UserClaims | None = claims

    def user(self) -> UserClaims | None:
        """The verified principal, or ``None`` for an anonymous request."""
        return self._claims

    def _verified(self) -> UserClaims:
        if self._claims is None:
            logger.warning(
                "identity_auth_failed reason_code=%s",
                "missing_token",
            )
            raise _unauthorized("Authentication required")
        return self._claims

    @property
    def profile_id(self) -> str | None:
        return self._verified().profile_id

    @property
    def subject(self) -> str:
        return self._verified().subject

    @property
    def profile(self) -> dict[str, object] | None:
        return self._verified().profile

    @property
    def identity(self) -> _ClaimsProxy:
        return self._verified().identity

    @property
    def roles(self) -> list[str]:
        return [] if self._claims is None else self._claims.roles

    def bearer_token(self) -> str:
        """The principal's bearer token (``Auth.token()``); 401 when anonymous."""
        return self._verified().bearer_token()

    def has_role(self, role: object) -> bool:
        """Whether the verified principal holds exactly *role*; ``False`` when anonymous."""
        return False if self._claims is None else self._claims.has_role(role)


def _enforce_route(
    user: UserClaims,
    providers: Sequence[str],
    roles: Sequence[object],
    principal_types: Sequence[str],
) -> None:
    """The route's own provider list, principal types and roles, in that order.

    Raises:
        AuthorizationDenied: Provider not allowed, principal type not admitted,
            or none of the roles held (each with its own reason code).
    """
    check_providers(user, providers)
    if principal_types:
        check_principal_types(user, principal_types)
    if roles:
        check_roles(user, roles)


def authorize_principal(
    user: UserClaims,
    *,
    providers: Sequence[str],
    roles: Sequence[object],
    principal_types: Sequence[str],
) -> UserClaims:
    """Enforce a route's contract on an already-verified principal.

    Raises:
        HTTPException: 403 (opaque) for a principal the contract refuses.
    """
    try:
        _enforce_route(user, providers, roles, principal_types)
    except AuthorizationDenied as exc:
        logger.warning("identity_authz_denied reason_code=%s", exc.reason_code)
        raise _forbidden() from exc
    return user


async def _verify_presented(
    request: HTTPConnection,
    token: str,
    providers: Sequence[str],
    roles: Sequence[object],
    principal_types: Sequence[str],
) -> UserClaims:
    """Verify a presented credential and enforce the route's contract.

    Raises:
        HTTPException: 401 (opaque) for a credential that fails verification,
            403 (opaque) for a verified principal the contract refuses.
    """
    try:
        user = await authenticate_token(token, request)
    except AuthenticationFailed as exc:
        logger.warning("identity_auth_failed reason_code=%s", exc.reason_code)
        raise _unauthorized("Invalid or expired token") from exc
    except AuthorizationDenied as exc:
        logger.warning("identity_authz_denied reason_code=%s", exc.reason_code)
        raise _forbidden() from exc
    return authorize_principal(
        user, providers=providers, roles=roles, principal_types=principal_types
    )


def _presented_authorization(request: HTTPConnection) -> bool:
    """True when the request carries a non-blank ``Authorization`` header."""
    value = request.headers.get("authorization")
    return value is not None and bool(value.strip())


async def authorize_required(
    request: HTTPConnection,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    providers: Sequence[str],
    roles: Sequence[object],
    principal_types: Sequence[str],
) -> UserClaims:
    """AUTHENTICATED and SERVICE: no credential is 401 ``MISSING_TOKEN``.

    Raises:
        HTTPException: 401 / 403 as the guard table specifies; bodies are opaque.
    """
    if credentials is None:
        reason = (
            "malformed_token" if _presented_authorization(request) else "missing_token"
        )
        logger.warning("identity_auth_failed reason_code=%s", reason)
        raise _unauthorized("Authentication required")
    return await _verify_presented(
        request, credentials.credentials, providers, roles, principal_types
    )


async def authorize_optional(
    request: HTTPConnection,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    providers: Sequence[str],
    roles: Sequence[object],
    principal_types: Sequence[str],
) -> UserClaims | None:
    """OPTIONAL: an absent ``Authorization`` header is anonymous; anything
    presented is verified in full, and a presented credential that is unusable
    or fails verification is 401 -- never ignored.

    Returns:
        The verified principal, or ``None`` for an absent header.

    Raises:
        HTTPException: 401 / 403 as the guard table specifies; bodies are opaque.
    """
    if credentials is None:
        if not _presented_authorization(request):
            return None
        logger.warning(
            "identity_auth_failed reason_code=%s",
            "malformed_token",
        )
        raise _unauthorized("Invalid or expired token")
    return await _verify_presented(
        request, credentials.credentials, providers, roles, principal_types
    )


def require_route(
    *,
    providers: Sequence[str],
    roles: Sequence[object] = (),
    principal_types: Sequence[str] = (),
) -> Callable[[Request, HTTPAuthorizationCredentials | None], Awaitable[UserClaims]]:
    """Dependency for an AUTHENTICATED or SERVICE route: the principal, always."""

    async def _guard(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> UserClaims:
        user = await authorize_required(
            request,
            credentials,
            providers=providers,
            roles=roles,
            principal_types=principal_types,
        )
        return user

    return _guard


def require_optional_route(
    *,
    providers: Sequence[str],
    roles: Sequence[object] = (),
    principal_types: Sequence[str] = (),
) -> Callable[
    [Request, HTTPAuthorizationCredentials | None], Awaitable[OptionalCaller]
]:
    """Dependency for an OPTIONAL route: an ``OptionalCaller`` (anonymous when no header)."""

    async def _guard(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> OptionalCaller:
        user = await authorize_optional(
            request,
            credentials,
            providers=providers,
            roles=roles,
            principal_types=principal_types,
        )
        return OptionalCaller(user)

    return _guard
