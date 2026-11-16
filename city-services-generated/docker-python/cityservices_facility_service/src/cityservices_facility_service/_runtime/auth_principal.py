"""Verified-principal core of a generated service's ``auth`` module.

Emitted verbatim as ``<package>/_runtime/auth_principal.py`` beside the
``auth`` module of every service whose gateway profile declares JWT auth. The
``auth`` module imports these definitions and adds the credential chain and the
route guards on top of them: it subclasses :class:`PrincipalClaims` as
``UserClaims`` with the one member that reads through the chain
(``bearer_token``), and re-exports the readers and the bearer scheme.

Holds the principal's claims (:class:`PrincipalClaims`, :class:`ClaimsProxy`),
the exact role comparison every role check makes (:func:`role_value`), the
opaque 401 / 403 every refusal answers with (:func:`unauthorized`,
:func:`forbidden`), and the request-scoped user ids
(:data:`current_user_id_ctx`, :data:`current_user_subject_ctx`) with their
readers.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

# Set by the credential chain when a principal is verified; read by
# get_current_user_id() in model trait hooks.
# current_user_id_ctx holds the RESOLVED local id (profile_id when projection is
# enabled, otherwise local_user_id() under the provider's localIdentity mode).
# current_user_subject_ctx always holds the raw provider sub.
# The route guard (require_route / require_optional_route) writes
# request.state.user_id with the resolved local id before any endpoint handler
# code runs. The raw claims.get("sub") is never the final value: a non-UUID
# subject in a UUID column fails at runtime.
current_user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_id", default=None
)
current_user_subject_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_subject", default=None
)
security: HTTPBearer = HTTPBearer(auto_error=False)


class ClaimsProxy:
    """Attribute-access shim over a JWT claims dict.

    Enables ``Auth.identity.<field>`` DSL expressions to work as Python
    attribute access on the principal's identity. Missing claims return ``None``
    rather than raising ``AttributeError``, matching DSL null-safety semantics.

    Example::

        # DSL: Auth.identity.email
        # Generated: current_user.identity.email
        claims_proxy = ClaimsProxy({"email": "alice@example.com"})
        assert claims_proxy.email == "alice@example.com"
        assert claims_proxy.missing is None
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, object]) -> None:
        object.__setattr__(self, "_data", data)

    def _claims(self) -> dict[str, object]:
        data: dict[str, object] = object.__getattribute__(self, "_data")
        return data

    def __getattr__(self, name: str) -> object:
        return self._claims().get(name)

    def get(self, key: str, default: object = None) -> object:
        """Dict-compatible read of one verified claim."""
        return self._claims().get(key, default)


def role_value(role: object) -> str:
    """The comparable value of *role*: an enum member's value, else its text."""
    return str(role.value if hasattr(role, "value") else role)


class PrincipalClaims:
    """Authenticated user claims extracted from JWT token.

    Attributes:
        profile_id: Resolved local user id — the projected IdentityProfile.profileId when
            projection is enabled for the provider, otherwise the raw JWT ``sub`` claim.
            This is the canonical user id for all application-layer lookups.
        id: Compatibility alias for ``profile_id`` (resolved local id, NOT the raw sub).
        subject: Raw JWT ``sub`` claim (provider-issued principal identifier).
        sub: Raw JWT ``sub`` claim; kept for backwards compatibility.
        profile: Projected IdentityProfile row dict when projection is enabled and the
            profile was loaded, otherwise ``None``.  Exposes the full profile document
            so ``Auth.profile.<field>`` DSL access works without a second DB lookup.
        identity: Attribute-access proxy over what ``Auth.identity.<field>`` reads: the
            verified claims, with each field the provider declares read through its
            claim path.  Returns ``None`` for a missing one — never raises ``AttributeError``.
        claims: The verified claims as the token carries them, for what reads the token
            itself (revocation, the tenant claim); a declared field never shadows one.
        roles: List of role names from the JWT.
        token: Raw JWT token string.
        plan: Subscription plan id from ``plan``, ``planId``, or ``plan_id`` claim (may be empty).
        provider: Logical provider name the verified token is attributed to
            (issuer AND audience resolved); empty when not attributable (e.g. an
            anonymous principal).
        expires_at: The verified ``exp`` claim (epoch seconds), or ``None`` when
            the token carries none. A connection-scoped handshake refuses a
            principal without it.
        tenant_id: The principal's own tenant, when one is attributable to the
            credential itself (an API key's row) or to the profile-store row of a
            provider whose tenant claim is an app-owned write-back field of this
            service's own store; ``None`` for a principal that carries no tenant.
    """

    __slots__ = (
        "profile_id",
        "id",
        "subject",
        "sub",
        "profile",
        "identity",
        "claims",
        "roles",
        "token",
        "plan",
        "provider",
        "expires_at",
        "tenant_id",
    )

    def __init__(
        self,
        sub: str,
        roles: list[str],
        token: str,
        plan: str,
        provider: str,
        profile_id: str | None = None,
        profile: dict[str, object] | None = None,
        identity: dict[str, object] | None = None,
        claims: dict[str, object] | None = None,
        expires_at: float | None = None,
        tenant_id: str | None = None,
    ) -> None:
        # profile_id is the resolved local id: projected IdentityProfile.profileId when
        # projection is enabled, raw sub otherwise.  id aliases profile_id for compatibility.
        self.profile_id: str | None = (
            profile_id if profile_id is not None else (sub or None)
        )
        self.id: str | None = self.profile_id
        self.subject: str = sub
        self.sub: str = sub
        self.profile: dict[str, object] | None = profile
        self.identity: ClaimsProxy = ClaimsProxy(
            identity if identity is not None else {}
        )
        self.claims: dict[str, object] = claims if claims is not None else {}
        self.roles = roles
        self.token = token
        self.plan = plan
        self.provider = provider
        self.expires_at: float | None = expires_at
        self.tenant_id: str | None = tenant_id

    def user(self) -> PrincipalClaims:
        """This principal (``Auth.user()``); never ``None`` for a verified principal."""
        return self

    def has_role(self, role: object) -> bool:
        """Whether this principal holds exactly *role* (``Auth.hasRole``).

        The comparison the route guard's role check (``check_roles``) makes:
        exact and case-sensitive, so a body's role test and the route's role
        gate cannot disagree.
        """
        wanted = role_value(role)
        return any(role_value(held) == wanted for held in self.roles)


def unauthorized(detail: str) -> HTTPException:
    """The opaque 401 every failed authentication answers with."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden() -> HTTPException:
    """The opaque 403 every authorization denial answers with."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


def get_current_user_id() -> str | None:
    """Return the resolved local user id from request context.

    Returns the projected IdentityProfile.profileId when projection is enabled
    for the provider, or local_user_id() under the provider's localIdentity
    mode otherwise (a UUID unless the mode is subjectText). ``None`` outside an
    authenticated request. Used by the Auditable stamp listeners and the audit
    log, and by model trait hooks that call Auth.userId() or
    get_current_user_id() outside of a FastAPI dependency context.
    """
    return current_user_id_ctx.get()


@contextmanager
def bind_current_user_id(user_id: str | None) -> Iterator[None]:
    """Make *user_id* what :func:`get_current_user_id` answers for the enclosed block.

    For a run with no request behind it that still acts for a caller: a resumed
    approval run's ``Auth.userId()`` and its audit stamps name the requester. Only
    ``principal_context.bind_principal`` calls it, and it binds no claims, so every
    other ``Auth`` read stays refused on that path.
    """
    token = current_user_id_ctx.set(user_id)
    try:
        yield
    finally:
        current_user_id_ctx.reset(token)


def get_current_user_subject() -> str | None:
    """Return the raw provider subject (JWT sub) from request context.

    Always returns the raw provider-issued sub, regardless of projection state.
    Use this when you need the unresolved provider identity (e.g. for audit logs).
    """
    return current_user_subject_ctx.get()
