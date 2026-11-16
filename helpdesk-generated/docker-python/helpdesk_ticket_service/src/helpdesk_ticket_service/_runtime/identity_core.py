"""JWKS-based identity validation core of a generated service.

Emitted verbatim as ``<package>/_runtime/identity_core.py`` of every service that
validates provider tokens. The service's ``identity`` module binds it once: it
passes the reason codes (:class:`IdentityReasons`), its ``config._bootstrap``
module (:class:`IdentityBootstrap`) and the provider-plan schema version it was
generated for, and re-exports the bound functions.

Loads the identity provider plan from the deployment-static path the bootstrap
module carries (``IDENTITY_PROVIDER_PLAN_PATH``).  Resolves signing keys via
``PyJWKClient`` with per-provider caching, and performs full token validation:
signature, expiry, issuer, audience, and algorithm allow-list.

Environment reads — exactly one, by design.  Plan *location* still reads no
environment variables.  Plan *content* does: a provider entry may declare
``allowedAudienceRefs``, a list of environment-variable NAMES (never values)
whose contents are unioned into the effective audience allow-list at runtime.
This exists because some accepted ``aud`` values are assigned by the identity
provider at provisioning time and so cannot be baked into a static plan — the
Entra v2 access token case, whose ``aud`` is the app registration's
deploy-time-assigned client-ID GUID delivered as the
``IDENTITY_<PROVIDER>_AUDIENCE_CLIENT_ID`` app setting.  The runtime contract is

    effective_audiences = allowedAudiences U {env[name] for name in refs}

and it FAILS CLOSED: a declared ref whose environment variable is unset or empty
raises ``JwksValidationError`` (``provider_config_error``).  It can never degrade
to an empty allow-list, which this module reads as "no audience constraint" (the
JWT decode is then passed ``audience=None``) — that degradation would drop
audience enforcement entirely for the affected provider.

Algorithm allow-list comes from the plan — symmetric algorithms (HS*) and
``alg: none`` are always rejected.  JWKS key rotation is handled by refreshing
the JWKS cache on unknown ``kid`` before rejecting.  JWKS refresh failure fails
closed.

Signing keys are fetched from the entry's ``jwksFetch.url`` when the plan
declares one -- presenting ``jwksFetch.hostHeader`` as the ``Host`` header when
given -- and from ``jwksUri`` otherwise.  ``jwksFetch`` exists for an identity
server whose public origin is unreachable from inside the deployment's own
network; it never changes which issuer a token must carry.  An ``https`` fetch
keeps the default certificate and host-name verification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import jwt
from jwt import PyJWK, PyJWKClient, PyJWKClientError, PyJWTError
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    PyJWKSetError,
)

from .mfa_introspection import FactorIntrospection, FactorIntrospectionUnavailable
from .plan_endpoint_checks import EndpointProblem, check_fetch_url, check_host_header

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYMMETRIC_ALG_PREFIXES: tuple[str, ...] = ("HS",)
_ALG_NONE: str = "none"

# Filename of the identity provider plan artifact bundled INTO the service
# package (beside ``config/_bootstrap.py``). Emitted per-service so it ships in
# the service wheel and resolves regardless of CWD — the same delivery pattern
# as ``config/remote_defaults.json``.
_PLAN_ARTIFACT_FILENAME: str = "identity-provider-plan.json"

# The credential kinds a provider plan entry may declare. Only a ``jwt`` entry
# is ever matched against a bearer token; an ``apiKey`` entry carries no issuer
# or signing keys. An entry declaring any other kind -- or none -- is refused at
# load, never read as a token provider by default.
_CREDENTIAL_JWT: str = "jwt"
_CREDENTIAL_API_KEY: str = "apiKey"
_KNOWN_CREDENTIALS: frozenset[str] = frozenset({_CREDENTIAL_JWT, _CREDENTIAL_API_KEY})

# A JWT entry's optional signing-key fetch endpoint: the in-network address the
# key set is fetched from when ``jwksUri`` (the public origin) is unreachable,
# and the ``Host`` header to present there. The object carries exactly these
# members; any other member, a non-``http(s)`` URL, a URL carrying user
# information or a fragment, or a Host header that is not a bare host[:port] is
# refused at load -- never fetched.
_JWKS_FETCH_MEMBER: str = "jwksFetch"
_JWKS_FETCH_URL: str = "url"
_JWKS_FETCH_HOST_HEADER: str = "hostHeader"
_JWKS_FETCH_KEYS: frozenset[str] = frozenset({_JWKS_FETCH_URL, _JWKS_FETCH_HOST_HEADER})
_HOST_HEADER_NAME: str = "Host"

# A ``mfa = "required"`` provider's entry carries ``mfaFactorProof``: the claim listing
# the authentication methods a sign-in completed, the values proving a second factor, and
# where the claim is read -- the verified access token (``source`` = ``token``) or the
# provider's introspection answer about it (``introspection``, with the object saying
# where to ask). The introspection object carries exactly these members.
_MFA_PROOF_MEMBER: str = "mfaFactorProof"
_PROOF_SOURCE_MEMBER: str = "source"
_PROOF_INTROSPECTION_MEMBER: str = "introspection"
_PROOF_SOURCE_TOKEN: str = "token"
_PROOF_SOURCE_INTROSPECTION: str = "introspection"
_PROOF_SOURCES: frozenset[str] = frozenset(
    {_PROOF_SOURCE_TOKEN, _PROOF_SOURCE_INTROSPECTION}
)
_INTROSPECTION_CREDENTIAL_FILE: str = "credentialFile"
_INTROSPECTION_CACHE_SECONDS: str = "cacheSeconds"
_INTROSPECTION_CACHE_SECONDS_MAX: int = 60
_INTROSPECTION_KEYS: frozenset[str] = frozenset(
    {
        _JWKS_FETCH_URL,
        _JWKS_FETCH_HOST_HEADER,
        _INTROSPECTION_CREDENTIAL_FILE,
        _INTROSPECTION_CACHE_SECONDS,
    }
)
# One introspection request's timeout, and the bound on the in-process cache of proving
# answers (least-recently-used eviction), as the revocation introspection check has.
_INTROSPECTION_TIMEOUT_SECONDS: int = 5
_INTROSPECTION_CACHE_MAX_ENTRIES: int = 10000

# ---------------------------------------------------------------------------
# Binding parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityReasons:
    """The reason codes token validation reports, bound by the service.

    Each is a value of the shared reason-code vocabulary. They are carried on
    :class:`JwksValidationError` and logged, never returned to a caller.
    """

    malformed_token: str
    expired_token: str
    bad_signature: str
    issuer_mismatch: str
    audience_mismatch: str
    provider_mismatch: str
    jwks_refresh_failed: str
    provider_config: str
    required_field_missing: str
    mfa_required: str


class IdentityBootstrap(Protocol):
    """What the core reads from the service's ``config._bootstrap`` module.

    The generated bootstrap module satisfies it. Its plan path is read on every
    plan resolution, never captured at bind time, and its ``__file__`` (when it
    has one) locates the plan bundled beside it.
    """

    @property
    def IDENTITY_PROVIDER_PLAN_PATH(self) -> str | None:
        """The deployment-static plan mount path; empty when the plan is bundled."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JwksValidationError(Exception):
    """Raised when JWKS-based token validation fails.

    Attributes:
        reason_code: One of the :class:`IdentityReasons` codes identifying the
            failure category.  Never exposed in client HTTP responses.
    """

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code: str = reason_code


# ---------------------------------------------------------------------------
# Plan documents
# ---------------------------------------------------------------------------


def plan_object(value: object, what: str) -> dict[str, object]:
    """*value* as one JSON object of the plan; anything else is a malformed plan.

    Raises:
        RuntimeError: *value* is not an object, naming *what* (never the value).
    """
    if not isinstance(value, dict):
        raise RuntimeError(
            "Identity provider plan: %s is not an object (found %s). Regenerate the "
            "service and its plan together." % (what, type(value).__name__)
        )
    return value


def plan_string(value: object, what: str) -> str:
    """*value* as a string member of the plan; anything else is a malformed plan.

    Raises:
        RuntimeError: *value* is not a string, naming *what* (never the value).
    """
    if not isinstance(value, str):
        raise RuntimeError(
            "Identity provider plan: %s is not a string (found %s). Regenerate the "
            "service and its plan together." % (what, type(value).__name__)
        )
    return value


def plan_list(value: object, what: str) -> list[object]:
    """*value* as a JSON array of the plan; anything else is a malformed plan.

    Raises:
        RuntimeError: *value* is not an array, naming *what* (never the value).
    """
    if not isinstance(value, list):
        raise RuntimeError(
            "Identity provider plan: %s is not an array (found %s). Regenerate the "
            "service and its plan together." % (what, type(value).__name__)
        )
    return value


def plan_providers(plan: dict[str, object]) -> dict[str, object]:
    """The plan's ``providers`` object, keyed by logical provider name."""
    return plan_object(plan.get("providers"), "'providers'")


def plan_provider_entry(
    plan: dict[str, object], provider_name: str
) -> dict[str, object]:
    """One provider's plan entry.

    Raises:
        KeyError: *provider_name* is absent from the plan.
        RuntimeError: The entry is not an object.
    """
    return plan_object(
        plan_providers(plan)[provider_name], "provider %r" % provider_name
    )


def _require_known_credentials(plan_path: str, plan: dict[str, object]) -> None:
    """Refuse a plan whose ``providers`` map or any entry's ``credential`` is unusable.

    Fails closed: a missing or non-object ``providers`` map, a non-object entry,
    or an entry whose ``credential`` is absent or not one of
    :data:`_KNOWN_CREDENTIALS` aborts the load. An entry is never assumed to be
    a token provider because it failed to say what it is.

    Raises:
        RuntimeError: Naming the offending provider and the accepted kinds.
    """
    providers = plan.get("providers")
    if not isinstance(providers, dict):
        raise RuntimeError(
            "Identity provider plan %r has no 'providers' object (found %s). "
            "Regenerate the service and its plan together."
            % (plan_path, type(providers).__name__)
        )
    for name, entry in providers.items():
        credential = entry.get("credential") if isinstance(entry, dict) else None
        if credential not in _KNOWN_CREDENTIALS:
            raise RuntimeError(
                "Identity provider plan %r: provider %r declares credential %r, but "
                "this runtime accepts only %s. Regenerate the service and its plan "
                "together so both carry the same schema."
                % (plan_path, name, credential, sorted(_KNOWN_CREDENTIALS))
            )


def _check_jwks_fetch(fetch: object) -> None:
    """Refuse a JWT entry's ``jwksFetch`` object unless it is usable.

    The object carries a required ``url`` and an optional ``hostHeader`` and
    nothing else.

    Raises:
        EndpointProblem: Naming the member at fault, never its value.
    """
    if not isinstance(fetch, dict):
        raise EndpointProblem("it is not an object")
    undeclared = sorted(str(key) for key in fetch if key not in _JWKS_FETCH_KEYS)
    if undeclared:
        raise EndpointProblem("it carries undeclared member(s) %s" % undeclared)
    if _JWKS_FETCH_URL not in fetch:
        raise EndpointProblem("it has no 'url'")
    check_fetch_url(fetch[_JWKS_FETCH_URL])
    if _JWKS_FETCH_HOST_HEADER not in fetch or fetch[_JWKS_FETCH_HOST_HEADER] is None:
        return
    check_host_header(fetch[_JWKS_FETCH_HOST_HEADER])


def _check_factor_proof(proof: object) -> None:
    """Refuse a JWT entry's ``mfaFactorProof`` object unless it is usable.

    Beside the claim and its proving values, it names where the claim is read:
    ``source`` is ``token`` (the verified access token) or ``introspection`` (the
    provider's answer about the token). An ``introspection`` source carries the
    ``introspection`` object -- ``url`` and optional ``hostHeader`` as ``jwksFetch``
    does, the ``credentialFile`` holding the signing key, and ``cacheSeconds`` -- and
    a ``token`` source carries none, because the runtime would read nothing from it.

    Raises:
        EndpointProblem: Naming the member at fault, never its value.
    """
    if not isinstance(proof, dict):
        raise EndpointProblem("it is not an object")
    source = proof.get(_PROOF_SOURCE_MEMBER)
    if source not in _PROOF_SOURCES:
        raise EndpointProblem("'source' is not one of %s" % sorted(_PROOF_SOURCES))
    endpoint = proof.get(_PROOF_INTROSPECTION_MEMBER)
    if source == _PROOF_SOURCE_TOKEN:
        if endpoint is not None:
            raise EndpointProblem("a 'token' source carries an 'introspection' object")
        return
    if not isinstance(endpoint, dict):
        raise EndpointProblem("an 'introspection' source has no 'introspection' object")
    undeclared = sorted(str(key) for key in endpoint if key not in _INTROSPECTION_KEYS)
    if undeclared:
        raise EndpointProblem(
            "'introspection' carries undeclared member(s) %s" % undeclared
        )
    check_fetch_url(endpoint.get(_JWKS_FETCH_URL))
    if endpoint.get(_JWKS_FETCH_HOST_HEADER) is not None:
        check_host_header(endpoint[_JWKS_FETCH_HOST_HEADER])
    credential_file = endpoint.get(_INTROSPECTION_CREDENTIAL_FILE)
    if not isinstance(credential_file, str) or not credential_file:
        raise EndpointProblem(
            "'introspection.credentialFile' is not a non-empty string"
        )
    cache_seconds = endpoint.get(_INTROSPECTION_CACHE_SECONDS)
    if (
        isinstance(cache_seconds, bool)
        or not isinstance(cache_seconds, int)
        or not 0 <= cache_seconds <= _INTROSPECTION_CACHE_SECONDS_MAX
    ):
        raise EndpointProblem(
            "'introspection.cacheSeconds' is not an integer from 0 to %d"
            % _INTROSPECTION_CACHE_SECONDS_MAX
        )


def _require_usable_factor_proof(plan_path: str, plan: dict[str, object]) -> None:
    """Refuse a plan whose JWT entry declares an unusable ``mfaFactorProof`` object.

    Fails closed: a proof the runtime cannot read exactly would otherwise admit tokens
    of a provider that requires a second factor.

    Raises:
        RuntimeError: Naming the provider and the problem, never the value.
    """
    for name in plan_providers(plan):
        entry = plan_provider_entry(plan, name)
        if (
            entry["credential"] != _CREDENTIAL_JWT
            or entry.get(_MFA_PROOF_MEMBER) is None
        ):
            continue
        try:
            _check_factor_proof(entry[_MFA_PROOF_MEMBER])
        except EndpointProblem as problem:
            raise RuntimeError(
                "Identity provider plan %r: provider %r declares an unusable %r: %s. "
                "Regenerate the service and its plan together."
                % (plan_path, name, _MFA_PROOF_MEMBER, problem)
            ) from problem


def _require_usable_jwks_fetch(plan_path: str, plan: dict[str, object]) -> None:
    """Refuse a plan whose JWT entry declares an unusable ``jwksFetch`` object.

    Fails closed: the runtime never fetches signing keys from an endpoint the
    plan does not describe exactly. An absent or ``null`` member means "fetch
    ``jwksUri``".

    Raises:
        RuntimeError: Naming the provider and the problem, never the value.
    """
    for name in plan_providers(plan):
        entry = plan_provider_entry(plan, name)
        if (
            entry["credential"] != _CREDENTIAL_JWT
            or entry.get(_JWKS_FETCH_MEMBER) is None
        ):
            continue
        try:
            _check_jwks_fetch(entry[_JWKS_FETCH_MEMBER])
        except EndpointProblem as problem:
            raise RuntimeError(
                "Identity provider plan %r: provider %r declares an unusable %r: %s. "
                "Expected an object with an 'http'/'https' 'url' naming a host (no "
                "user information, fragment or whitespace) and an optional bare "
                "host[:port] 'hostHeader', and no other member. Regenerate the "
                "service and its plan together."
                % (plan_path, name, _JWKS_FETCH_MEMBER, problem)
            ) from problem


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


def _resolve_claim_path(claims: dict[str, object], claim_path: str) -> object:
    """Resolve a (possibly dotted) claim path against the decoded claims.

    Traverses nested mappings segment by segment so providers whose roles live
    under a nested object (e.g. ``realm_access.roles``) resolve correctly,
    while a flat key (``roles``) still works as a single-segment path.  Returns
    ``None`` when any segment is missing or a non-mapping value is reached before
    the path is fully consumed — never a flat lookup of a key literally named
    ``"realm_access.roles"``.

    Args:
        claims: Decoded JWT claims dict.
        claim_path: Dot-separated claim path (e.g. ``"realm_access.roles"``).

    Returns:
        The value at the claim path, or ``None`` when it cannot be resolved.
    """
    cursor: object = claims
    for segment in claim_path.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(segment)
    return cursor


def _extract_roles(claims: dict[str, object], provider: dict[str, object]) -> list[str]:
    """Extract CruftFree role strings from token claims using the provider's roleSource.

    Two claim shapes are supported:

    * **Map shape** -- the self-host (Zitadel) default role claim
      ``urn:zitadel:iam:org:project:roles`` resolves to a mapping
      ``{roleKey: {orgId: orgDomain}}``. The role KEYS are the role names; the
      nested ``{orgId: orgDomain}`` values are organization metadata and are not
      role names.
    * **Array shape** -- ``external`` OIDC providers may deliver the claim as a
      flat list of role-name strings (e.g. ``["editor", "viewer"]``).

    Every raw role name is then normalized through ``roleMappings`` (provider-local
    role name -> CruftFree role name); unmapped names pass through unchanged.

    Args:
        claims: Decoded JWT claims dict.
        provider: Provider plan entry dict.

    Returns:
        List of normalized role name strings.
    """
    raw_role_source = provider.get("roleSource")
    claim_path = (
        "roles"
        if raw_role_source is None
        else plan_string(
            plan_object(raw_role_source, "roleSource").get("claimPath", "roles"),
            "roleSource.claimPath",
        )
    )
    raw_claim = _resolve_claim_path(claims, claim_path)
    if isinstance(raw_claim, dict):
        raw_roles: list[str] = [str(key) for key in raw_claim]
    elif isinstance(raw_claim, list):
        raw_roles = [str(item) for item in raw_claim]
    else:
        raw_roles = []
    role_mappings = plan_object(provider.get("roleMappings", {}), "roleMappings")
    return [str(role_mappings.get(raw, raw)) for raw in raw_roles]


def _token_audiences(unverified_payload: dict[str, object]) -> set[str]:
    """Return the token's ``aud`` claim normalized to a set of strings.

    The JWT ``aud`` claim is either a single string or a list of strings
    (RFC 7519).  Both shapes are normalized so provider selection can intersect
    it against each provider's ``allowedAudiences``.

    Args:
        unverified_payload: The decoded (unverified) JWT payload.

    Returns:
        Set of audience strings; empty when ``aud`` is absent or malformed.
    """
    raw = unverified_payload.get("aud")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    return set()


# ---------------------------------------------------------------------------
# The bound core
# ---------------------------------------------------------------------------


class IdentityCore:
    """Token validation and provider-plan access for one service.

    Holds the loaded plan and the signing-key clients, so one instance per
    service process is the cache. The service's ``identity`` module creates that
    instance and exposes its bound methods.
    """

    def __init__(
        self,
        *,
        reasons: IdentityReasons,
        bootstrap: IdentityBootstrap,
        plan_schema_version: int,
    ) -> None:
        """Bind the core to a service.

        Args:
            reasons: The reason codes failures carry.
            bootstrap: The service's bootstrap module, which locates the plan.
            plan_schema_version: The one provider-plan schema version this
                service was generated for. A plan carrying any other version is
                refused at load rather than read under a shape the service was
                not generated for.
        """
        self._reasons = reasons
        self._bootstrap = bootstrap
        self._plan_schema_version = plan_schema_version
        self._cached_plan: dict[str, object] | None = None
        self._cached_plan_path: str | None = None
        self._jwks_clients: dict[str, PyJWKClient] = {}
        self._factor_introspection = FactorIntrospection(
            timeout_seconds=_INTROSPECTION_TIMEOUT_SECONDS,
            cache_max_entries=_INTROSPECTION_CACHE_MAX_ENTRIES,
        )

    def clear_caches(self) -> None:
        """Forget the loaded plan and every signing-key client.

        The next call reloads the plan from its resolved path and creates fresh
        key-set clients. A service's tests call it between cases so a plan from
        one case cannot reach another.
        """
        self._cached_plan = None
        self._cached_plan_path = None
        self._jwks_clients.clear()

    # -- Plan loading -------------------------------------------------------

    def _bundled_plan_path(self) -> Path | None:
        """Return the module-relative path to the bundled plan, or None when unknown.

        ``_bootstrap`` lives in the service's ``config`` package, so the bundled
        plan sits next to it inside the installed wheel.  ``Path(__file__)``-style
        resolution is CWD-independent (unlike a bare relative ``open(...)``), so it
        resolves under site-packages on Azure App Service / any wheel install.

        Returns ``None`` when the bootstrap module exposes no ``__file__`` (e.g. a
        dynamically constructed module), in which case the baked mount path is
        used.
        """
        bootstrap_file = getattr(self._bootstrap, "__file__", None)
        if not bootstrap_file:
            return None
        return Path(bootstrap_file).with_name(_PLAN_ARTIFACT_FILENAME)

    def _resolve_plan_path(self) -> str:
        """Resolve the on-disk identity provider plan path (no environment reads).

        Resolution order (deployment-static, CWD-independent):

        1. The plan artifact BUNDLED beside ``_bootstrap`` inside the installed
           service package (``config/identity-provider-plan.json``). This ships
           in the service wheel and always resolves under site-packages
           regardless of the process working directory — the primary path for
           wheel deployments (Azure App Service, AWS).
        2. The deployment-static ``_bootstrap.IDENTITY_PROVIDER_PLAN_PATH``
           constant — used when the plan is mounted at a fixed absolute path
           rather than bundled (e.g. the docker-compose read-only mount).

        Returns:
            The resolved plan path as a string.

        Raises:
            RuntimeError: When neither a bundled artifact nor a baked path is
                available.
        """
        bundled = self._bundled_plan_path()
        if bundled is not None and bundled.is_file():
            return str(bundled)
        baked_path = self._bootstrap.IDENTITY_PROVIDER_PLAN_PATH or ""
        if baked_path:
            return baked_path
        raise RuntimeError(
            "Identity provider plan not found: no bundled plan artifact beside "
            "_bootstrap (%r) and the deployment-static 'IDENTITY_PROVIDER_PLAN_PATH' "
            "bootstrap constant is empty. The plan must ship inside the service "
            "package (config/%s) or be mounted at the baked path. Regenerate the "
            "service." % (str(bundled), _PLAN_ARTIFACT_FILENAME)
        )

    def _load_provider_plan(self) -> dict[str, object]:
        """Load and cache the identity provider plan (no environment reads).

        The plan is resolved by :meth:`_resolve_plan_path` — bundled artifact
        first (CWD-independent, ships in the wheel), then the deployment-static
        mount path.

        Returns:
            Parsed plan dict.

        Raises:
            RuntimeError: When no plan can be resolved, the file cannot be read,
                the plan's ``schemaVersion`` is not the one this service
                supports, a provider entry declares no known ``credential`` kind,
                or a JWT entry declares an unusable ``jwksFetch`` object.
        """
        plan_path = self._resolve_plan_path()
        if self._cached_plan is not None and self._cached_plan_path == plan_path:
            return self._cached_plan
        with open(plan_path, encoding="utf-8") as fh:
            plan = plan_object(json.load(fh), "the plan document")
        plan_version = plan.get("schemaVersion")
        if plan_version != self._plan_schema_version:
            raise RuntimeError(
                "Identity provider plan %r declares schemaVersion %r, but this runtime "
                "supports schema version %d only. Regenerate the service and its plan "
                "together so both carry the same schema version."
                % (plan_path, plan_version, self._plan_schema_version)
            )
        _require_known_credentials(plan_path, plan)
        _require_usable_jwks_fetch(plan_path, plan)
        _require_usable_factor_proof(plan_path, plan)
        self._cached_plan = plan
        self._cached_plan_path = plan_path
        logger.debug(
            "identity_plan_loaded path=%s providers=%s",
            plan_path,
            list(plan_providers(plan)),
        )
        return plan

    def load_provider_plan(self) -> dict[str, object]:
        """Public accessor for the cached identity provider plan.

        Token validation and profile projection resolve ``providers`` through
        this single loader so plan loading and caching live in exactly one
        place.

        Returns:
            The parsed provider plan dict.

        Raises:
            RuntimeError: When no plan can be resolved or the file cannot be read.
        """
        return self._load_provider_plan()

    # -- Deterministic local-user-id resolver --------------------------------

    def local_user_id(self, provider_name: str, subject: str) -> str:
        """Resolve the stable local user id for (provider, sub) from the provider plan.

        Reads ``localIdentity.mode`` and — for ``deterministicUuid5`` — the frozen
        namespace from the provider plan entry.  The namespace is never declared
        as a literal in this package; it is always read from the plan at runtime.

        Modes:
            deterministicUuid5: ``uuidv5(namespace, "<provider>:<sub>")`` —
                UUID-shaped, stateless, uniform across all services for the same
                ``(provider, sub)`` pair.
            subjectText: raw subject verbatim — the app-level schema uses TEXT
                columns.

        The ``projected`` mode is handled by the profile store path instead;
        calling this resolver for a projected provider is a configuration error.

        Args:
            provider_name: Logical provider name (must be present in the plan).
            subject: Raw JWT ``sub`` claim.

        Returns:
            Resolved local user id string.

        Raises:
            JwksValidationError: When ``localIdentity.mode`` is ``projected`` or
                unknown.
            RuntimeError: When the provider plan cannot be loaded.
            KeyError: When ``provider_name`` is absent from the plan.
        """
        plan = self.load_provider_plan()
        entry = plan_provider_entry(plan, provider_name)
        local_identity = plan_object(
            entry["localIdentity"], "localIdentity of %r" % provider_name
        )
        mode = plan_string(
            local_identity["mode"], "localIdentity.mode of %r" % provider_name
        )
        if mode == "deterministicUuid5":
            namespace = uuid.UUID(
                plan_string(
                    local_identity["namespace"],
                    "localIdentity.namespace of %r" % provider_name,
                )
            )
            return str(uuid.uuid5(namespace, "%s:%s" % (provider_name, subject)))
        if mode == "subjectText":
            return subject
        raise JwksValidationError(
            reason_code=self._reasons.provider_config,
            message=(
                "local_user_id called for provider '%s' in mode '%s'; "
                "the 'projected' mode resolves via the profile store, not the "
                "deterministic resolver.  "
                "Fix: use load_or_create_profile for projected providers, or "
                "reconfigure the provider to use 'deterministicUuid5' or 'subjectText'."
                % (provider_name, mode)
            ),
        )

    # -- JWKS client cache (keyed by provider name + fetch URL [+ Host header]) --

    def _jwks_fetch_target(
        self, provider_name: str, entry: dict[str, object]
    ) -> tuple[str, dict[str, str]]:
        """The URL a JWT entry's signing keys are fetched from, and the headers to send.

        ``jwksFetch.url`` (with ``jwksFetch.hostHeader`` as the ``Host`` header,
        when given) when the entry declares the object; ``jwksUri`` otherwise.
        The loader has already refused an unusable ``jwksFetch`` object.

        Raises:
            JwksValidationError: ``provider_config_error`` when the entry declares
                neither a ``jwksFetch`` object nor a non-empty ``jwksUri`` --
                there is no key set to verify against, so the token is refused.
        """
        raw_fetch = entry.get(_JWKS_FETCH_MEMBER)
        if raw_fetch is not None:
            what = "%s of %r" % (_JWKS_FETCH_MEMBER, provider_name)
            fetch = plan_object(raw_fetch, what)
            headers: dict[str, str] = {}
            if fetch.get(_JWKS_FETCH_HOST_HEADER) is not None:
                headers[_HOST_HEADER_NAME] = plan_string(
                    fetch[_JWKS_FETCH_HOST_HEADER], what
                )
            return plan_string(fetch[_JWKS_FETCH_URL], what), headers
        jwks_uri = entry.get("jwksUri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise JwksValidationError(
                reason_code=self._reasons.provider_config,
                message=(
                    "Provider '%s' declares neither a 'jwksFetch' object nor a "
                    "'jwksUri'; its signing keys cannot be fetched, so the token is "
                    "refused.  Regenerate the service and its plan together."
                    % provider_name
                ),
            )
        return jwks_uri, {}

    def _get_jwks_client(
        self,
        provider_name: str,
        fetch_url: str,
        headers: dict[str, str],
        cache_ttl_seconds: int,
    ) -> PyJWKClient:
        """Return a cached ``PyJWKClient`` for the given provider's key-set endpoint.

        Args:
            provider_name: Logical provider name (used as cache key prefix).
            fetch_url: The URL the provider's key set is fetched from.
            headers: Headers sent with every fetch (the ``Host`` header of a
                ``jwksFetch`` endpoint, or none).
            cache_ttl_seconds: JWKS cache TTL in seconds.

        Returns:
            Shared ``PyJWKClient`` instance for this provider and endpoint.
        """
        cache_key = "|".join(
            (
                provider_name,
                fetch_url,
                *("%s=%s" % item for item in sorted(headers.items())),
            )
        )
        if cache_key not in self._jwks_clients:
            self._jwks_clients[cache_key] = PyJWKClient(
                fetch_url,
                cache_keys=True,
                lifespan=cache_ttl_seconds,
                headers=dict(headers),
            )
            # The provider names the key set; its fetch address and Host header stay
            # out of the log.
            logger.debug(
                "identity_jwks_client_created provider=%s ttl=%s",
                provider_name,
                cache_ttl_seconds,
            )
        return self._jwks_clients[cache_key]

    # -- Algorithm guard ----------------------------------------------------

    def _assert_asymmetric_algorithm(self, alg: str, provider_name: str) -> None:
        """Raise ``JwksValidationError`` when ``alg`` is symmetric or ``none``.

        Args:
            alg: JWS algorithm identifier.
            provider_name: Provider name for diagnostics.

        Raises:
            JwksValidationError: When the algorithm is rejected.
        """
        if alg.lower() == _ALG_NONE or any(
            alg.startswith(p) for p in _SYMMETRIC_ALG_PREFIXES
        ):
            raise JwksValidationError(
                reason_code=self._reasons.bad_signature,
                message=(
                    "Rejected algorithm '%s' for provider '%s': symmetric algorithms "
                    "(HS*) and 'none' are not permitted.  Use an asymmetric algorithm "
                    "(RS*, ES*, PS*)." % (alg, provider_name)
                ),
            )

    # -- Provider selection -------------------------------------------------

    def _effective_audiences(
        self, provider_name: str, provider: dict[str, object]
    ) -> list[str]:
        """Return the provider's effective audience allow-list, failing closed on unset refs.

        The effective allow-list is the union of the static ``allowedAudiences``
        and the resolved values of every environment variable NAMED in
        ``allowedAudienceRefs``.  Refs exist for audiences the identity provider
        assigns at provisioning time (the Entra v2 access token ``aud`` is the
        app registration's deploy-time client-ID GUID), which cannot be baked
        into a static plan.

        A declared ref whose environment variable is unset or empty is a
        deployment wiring defect, and it FAILS CLOSED with
        ``provider_config_error``.  It must never silently yield an empty
        allow-list: an empty allow-list means "no audience constraint" —
        :meth:`_select_provider` prefers such a provider as unconstrained, and
        the JWT decode is then passed ``audience=None``.  Degrading here would
        therefore drop audience enforcement entirely.

        Args:
            provider_name: Logical provider name (for diagnostics).
            provider: Provider plan entry dict.

        Returns:
            The effective audience allow-list, static entries first, then
            resolved refs in declaration order, de-duplicated.

        Raises:
            JwksValidationError: When a declared ref's environment variable is
                unset or empty.
        """
        audiences: list[str] = [
            str(a)
            for a in plan_list(provider.get("allowedAudiences", []), "allowedAudiences")
        ]
        seen: set[str] = set(audiences)
        for raw_ref in plan_list(
            provider.get("allowedAudienceRefs", []), "allowedAudienceRefs"
        ):
            ref_name: str = str(raw_ref)
            value: str = os.environ.get(ref_name, "").strip()
            if not value:
                logger.error(
                    "identity_audience_ref_unresolved provider=%s env_var=%s reason_code=%s",
                    provider_name,
                    ref_name,
                    self._reasons.provider_config,
                )
                raise JwksValidationError(
                    reason_code=self._reasons.provider_config,
                    message=(
                        "Provider '%s' declares the late-bound audience reference '%s' "
                        "in 'allowedAudienceRefs', but the environment variable '%s' is "
                        "unset or empty.  Expected: the audience value assigned by the "
                        "identity provider at provisioning time (for Entra, the app "
                        "registration's client-ID GUID).  Validation fails closed rather "
                        "than falling back to an unconstrained audience allow-list.  "
                        "Fix: deliver '%s' to this service as an application setting / "
                        "environment variable at deploy time."
                        % (provider_name, ref_name, ref_name, ref_name)
                    ),
                )
            if value not in seen:
                seen.add(value)
                audiences.append(value)
        return audiences

    def _select_provider(
        self,
        providers: dict[str, object],
        token_iss: str,
        token_aud: set[str],
    ) -> tuple[str, dict[str, object]] | None:
        """Select the provider plan entry matching the token's issuer and audience.

        A single OIDC instance (e.g. one Zitadel server) can host multiple
        projects that all share one issuer URL and differ only by audience (the
        project id carried in the token ``aud``).  Matching by issuer alone lets
        the first-declared provider win for every token from that instance, so a
        workforce token would be validated against the customer provider's
        ``allowedAudiences`` and fail with an audience mismatch.

        Selection rules, applied in order:

        1. Gather every ``jwt``-credential provider whose ``issuer`` equals
           ``token_iss``. An ``apiKey`` provider is never a candidate: it has no
           issuer and no signing keys a token could be verified against.
        2. When exactly one matches, use it (audience is enforced later by
           decode).
        3. When several share the issuer, prefer the one whose non-empty
           EFFECTIVE audience allow-list intersects the token ``aud``.
        4. Otherwise prefer a provider that does not constrain audience (an
           empty effective allow-list accepts any audience).
        5. Otherwise fall back to the first issuer match so validation still
           fails closed with a deterministic ``audience_mismatch``.

        "Effective" means :meth:`_effective_audiences` — static
        ``allowedAudiences`` unioned with the resolved ``allowedAudienceRefs``
        environment variables.  A declared ref that cannot be resolved raises
        rather than collapsing to an empty allow-list, so rule 4 can never be
        reached by an unresolved ref.

        Args:
            providers: The plan ``providers`` map (name -> entry).
            token_iss: The token's ``iss`` claim.
            token_aud: The token's ``aud`` claim normalized to a set.

        Returns:
            ``(provider_name, provider_entry)`` for the selected provider, or
            ``None`` when no provider's issuer matches the token.

        Raises:
            JwksValidationError: When an issuer-matched provider declares an
                audience ref whose environment variable is unset or empty.
        """
        entries = [
            (name, plan_object(raw, "provider %r" % name))
            for name, raw in providers.items()
        ]
        issuer_matches: list[tuple[str, dict[str, object]]] = [
            (name, entry)
            for name, entry in entries
            if entry.get("credential") == _CREDENTIAL_JWT
            and entry.get("issuer", "") == token_iss
        ]
        if not issuer_matches:
            return None
        if len(issuer_matches) == 1:
            return issuer_matches[0]
        resolved: list[tuple[str, dict[str, object], set[str]]] = [
            (name, entry, set(self._effective_audiences(name, entry)))
            for name, entry in issuer_matches
        ]
        for name, entry, allowed in resolved:
            if allowed & token_aud:
                return (name, entry)
        for name, entry, allowed in resolved:
            if not allowed:
                return (name, entry)
        return issuer_matches[0]

    def resolve_provider_name(self, claims: dict[str, object]) -> str | None:
        """Return the logical provider name that owns the given verified claims.

        Attributes a validated token to its true provider using the SAME issuer +
        audience selection as :meth:`validate_token_claims` (via
        :meth:`_select_provider`).  A single OIDC instance can host several
        providers that share one issuer and differ only by audience (the project
        id in ``aud``); matching by issuer alone would mis-attribute a token to
        the first provider sharing that issuer.

        Surface guards call this to attribute a validated token to its true
        provider and then enforce the surface's provider allow-list: a genuine
        token whose provider is not permitted on a surface is an authorization
        denial (403), not a validation failure (401) — e.g. a workforce token on a
        customer-only surface.

        Args:
            claims: Verified JWT claims (as returned by
                :meth:`validate_token_claims`).

        Returns:
            The logical provider name whose issuer + audience own the claims, or
            ``None`` when no provider's issuer matches (only possible for claims
            that did not originate from :meth:`validate_token_claims`).

        Raises:
            JwksValidationError: When an issuer-matched provider declares an
                audience ref whose environment variable is unset or empty
                (fail-closed).
        """
        plan = self._load_provider_plan()
        providers = plan_providers(plan)
        token_iss: str = str(claims.get("iss", ""))
        token_aud: set[str] = _token_audiences(claims)
        selection = self._select_provider(providers, token_iss, token_aud)
        return None if selection is None else selection[0]

    # -- Core validation ----------------------------------------------------

    async def validate_token_claims(self, token: str) -> dict[str, object]:
        """Validate a JWT and return its verified claims.

        All tokens are validated through the identity provider plan via JWKS.
        An unrecognized issuer fails closed with a reason code.

        Steps:
        1. Decode unverified payload to extract the ``iss`` and ``aud`` claims.
        2. Load provider plan, match provider by issuer (disambiguating by
           audience when several providers share one issuer), validate via JWKS.

        JWKS refresh failure fails closed: ``JwksValidationError`` with the
        ``jwks_refresh_failed`` reason is raised rather than allowing an
        unverifiable token through.

        Args:
            token: Raw JWT Bearer token string (no ``Bearer `` prefix).

        Returns:
            Verified claims dict with ``roles`` key populated.

        Raises:
            JwksValidationError: On any validation failure.
        """
        # Decode unverified payload first to extract the issuer for provider matching.
        unverified_payload = self._unverified_payload(token)
        token_iss: str = str(unverified_payload.get("iss", ""))

        # Load provider plan and validate via JWKS.
        plan = self._load_provider_plan()
        providers = plan_providers(plan)

        # Decode unverified header to identify algorithm and kid for JWKS lookup.
        unverified_header = self._unverified_header(token)
        token_alg: str = str(unverified_header.get("alg", ""))
        token_kid: str = str(unverified_header.get("kid", ""))

        # Match provider by issuer, disambiguating by audience when several
        # providers share one issuer (e.g. multiple Zitadel projects on a single
        # instance — identical issuer URL, distinct project-id audiences).
        token_aud: set[str] = _token_audiences(unverified_payload)
        selection = self._select_provider(providers, token_iss, token_aud)
        if selection is None:
            raise JwksValidationError(
                reason_code=self._reasons.provider_mismatch,
                message=(
                    "No configured provider matches the token issuer.  "
                    "Ensure the provider plan includes a provider with issuer "
                    "matching the token's 'iss' claim."
                ),
            )
        matched_provider_name, matched_provider = selection

        allowed_algorithms = self._allowed_algorithms(
            matched_provider_name, matched_provider, token_alg
        )
        signing_key = await self._signing_key(
            token, token_kid, matched_provider_name, matched_provider
        )

        # Full verification with asymmetric key.  Audiences are the EFFECTIVE
        # list: static allowedAudiences U resolved allowedAudienceRefs (fails
        # closed when a declared ref's env var is unset — never an unconstrained
        # empty list).
        allowed_audiences: list[str] = self._effective_audiences(
            matched_provider_name, matched_provider
        )
        claims = self._verified_claims(
            token, signing_key, allowed_algorithms, token_iss, allowed_audiences
        )

        # Populate roles from provider roleSource / roleMappings.
        claims["roles"] = _extract_roles(claims, matched_provider)
        self._require_identity_fields(claims, matched_provider_name, matched_provider)
        await self._require_mfa_factor_proof(
            token, claims, matched_provider_name, matched_provider
        )
        return claims

    def _unverified_payload(self, token: str) -> dict[str, object]:
        """The token's payload, decoded without verification, for provider matching.

        Raises:
            JwksValidationError: ``malformed_token`` when the payload cannot be
                decoded.
        """
        try:
            payload: dict[str, object] = jwt.decode(
                token, options={"verify_signature": False}
            )
        except PyJWTError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.malformed_token,
                message="Token payload could not be decoded: %s" % exc,
            ) from exc
        return payload

    def _unverified_header(self, token: str) -> dict[str, object]:
        """The token's header, decoded without verification, for the JWKS lookup.

        Raises:
            JwksValidationError: ``malformed_token`` when the header cannot be
                decoded.
        """
        try:
            header: dict[str, object] = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.malformed_token,
                message="Token header could not be decoded: %s" % exc,
            ) from exc
        return header

    def _allowed_algorithms(
        self, provider_name: str, provider: dict[str, object], token_alg: str
    ) -> list[str]:
        """The provider's algorithm allow-list, once the token's algorithm passes it.

        Raises:
            JwksValidationError: ``bad_signature`` when the allow-list itself
                names a symmetric algorithm or ``none``, when the token's
                algorithm is not on it, or when the token's algorithm is
                symmetric or ``none``.
        """
        allowed_algorithms: list[str] = [
            str(alg)
            for alg in plan_list(
                provider.get("allowedAlgorithms", []), "allowedAlgorithms"
            )
        ]

        # Guard: reject symmetric / none from the plan allow-list itself.
        for alg in allowed_algorithms:
            self._assert_asymmetric_algorithm(alg, provider_name)

        # Guard: token algorithm must be in plan allow-list.
        if token_alg not in allowed_algorithms:
            raise JwksValidationError(
                reason_code=self._reasons.bad_signature,
                message=(
                    "Token algorithm '%s' is not in the provider '%s' allow-list %r.  "
                    "The token must be signed with an algorithm declared in the "
                    "provider plan 'allowedAlgorithms'."
                    % (token_alg, provider_name, allowed_algorithms)
                ),
            )
        # Double-guard: reject symmetric regardless of plan allow-list.
        self._assert_asymmetric_algorithm(token_alg, provider_name)
        return allowed_algorithms

    async def _signing_key(
        self,
        token: str,
        token_kid: str,
        provider_name: str,
        provider: dict[str, object],
    ) -> PyJWK:
        """The provider key that signed *token*, refreshing the key set once on a miss.

        Raises:
            JwksValidationError: ``provider_config_error`` when the provider has
                no key-set endpoint; ``jwks_refresh_failed`` when the key is
                still not found after a refresh, or the refresh fails.
            RuntimeError: The plan's ``jwksCacheTtlSeconds`` is not an integer.
        """
        fetch_url, fetch_headers = self._jwks_fetch_target(provider_name, provider)
        raw_cache_ttl = provider["jwksCacheTtlSeconds"]
        if isinstance(raw_cache_ttl, bool) or not isinstance(raw_cache_ttl, int):
            raise RuntimeError(
                "Identity provider plan: jwksCacheTtlSeconds of %r is not an integer. "
                "Regenerate the service and its plan together." % provider_name
            )
        jwks_client = self._get_jwks_client(
            provider_name, fetch_url, fetch_headers, raw_cache_ttl
        )

        # Resolve signing key — on unknown kid, refresh JWKS once.
        try:
            return await asyncio.to_thread(jwks_client.get_signing_key_from_jwt, token)
        except (PyJWKClientError, PyJWKSetError):
            logger.warning(
                "identity_jwks_key_miss provider=%s kid=%s refreshing",
                provider_name,
                token_kid or "(none)",
            )
        try:
            await asyncio.to_thread(jwks_client.fetch_data)
            return await asyncio.to_thread(jwks_client.get_signing_key_from_jwt, token)
        except Exception as refresh_exc:
            logger.warning(
                "identity_jwks_refresh_failed provider=%s reason_code=%s",
                provider_name,
                self._reasons.jwks_refresh_failed,
            )
            raise JwksValidationError(
                reason_code=self._reasons.jwks_refresh_failed,
                message=(
                    "JWKS refresh failed for provider '%s': %s.  "
                    "The token cannot be verified (fail-closed)."
                    % (provider_name, refresh_exc)
                ),
            ) from refresh_exc

    def _verified_claims(
        self,
        token: str,
        signing_key: PyJWK,
        allowed_algorithms: list[str],
        token_iss: str,
        allowed_audiences: list[str],
    ) -> dict[str, object]:
        """The token's claims, once its signature, expiry, issuer and audience verify.

        Raises:
            JwksValidationError: Carrying the reason of the first failed check.
        """
        try:
            claims: dict[str, object] = jwt.decode(
                token,
                signing_key.key,
                algorithms=allowed_algorithms,
                issuer=token_iss,
                audience=allowed_audiences if allowed_audiences else None,
                options={"require": ["exp", "iss"]},
            )
        except ExpiredSignatureError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.expired_token,
                message="Token has expired.",
            ) from exc
        except InvalidSignatureError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.bad_signature,
                message="Token signature is invalid.",
            ) from exc
        except InvalidAudienceError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.audience_mismatch,
                message="Token audience does not match the expected audience.",
            ) from exc
        except InvalidIssuerError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.issuer_mismatch,
                message="Token issuer does not match the configured issuer.",
            ) from exc
        except DecodeError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.malformed_token,
                message="Token could not be decoded: %s" % exc,
            ) from exc
        except PyJWTError as exc:
            raise JwksValidationError(
                reason_code=self._reasons.bad_signature,
                message="Token verification failed: %s" % exc,
            ) from exc
        return claims

    def _require_identity_fields(
        self,
        claims: dict[str, object],
        provider_name: str,
        provider: dict[str, object],
    ) -> None:
        """Edge-enforce the provider's required identity fields on verified claims.

        Claims declared ``guarantee=required`` in ``attributeMappings`` must be
        present in the verified token; a missing claim is an opaque 401 (reason
        code to logs only) rather than a downstream 500.

        Raises:
            JwksValidationError: ``required_field_missing`` naming the field.
        """
        attribute_mappings = plan_object(
            provider.get("attributeMappings", {}), "attributeMappings"
        )
        for field_name, raw_field_cfg in attribute_mappings.items():
            field_cfg = plan_object(raw_field_cfg, "attributeMappings.%s" % field_name)
            if str(field_cfg.get("guarantee", "")) != "required":
                continue
            claim_path: str = str(field_cfg.get("claimPath", field_name))
            if _resolve_claim_path(claims, claim_path) is not None:
                continue
            logger.warning(
                "identity_auth_failed reason_code=%s field=%s provider=%s",
                self._reasons.required_field_missing,
                field_name,
                provider_name,
            )
            raise JwksValidationError(
                reason_code=self._reasons.required_field_missing,
                message=(
                    "Required identity field '%s' (claim path '%s') is absent from the "
                    "verified token for provider '%s'.  "
                    "The provider must include this claim in every issued token."
                    % (field_name, claim_path, provider_name)
                ),
            )

    async def _require_mfa_factor_proof(
        self,
        token: str,
        claims: dict[str, object],
        provider_name: str,
        provider: dict[str, object],
    ) -> None:
        """Refuse a token of a ``mfa = "required"`` provider that proves no second factor.

        The entry's ``mfaFactorProof`` names the claim listing the authentication methods
        the sign-in completed (an RFC 8176 ``amr`` array of strings) and the values any one
        of which proves a second factor; an entry without it asks for nothing. The claim is
        read from the verified token (``source`` = ``token``) or from the provider's
        introspection answer about it (``introspection``: a provider whose access tokens
        carry no authentication methods). The claim absent, not an array, or holding none
        of the values -- or, under ``introspection``, an answer that cannot be obtained --
        is an opaque 401 (reason code to logs only), never an allow: the service checks the
        proof itself rather than trusting the provider's configuration.

        Raises:
            JwksValidationError: ``mfa_required`` naming the provider and the claim.
            RuntimeError: The entry's ``mfaFactorProof`` is malformed.
        """
        raw_proof = provider.get(_MFA_PROOF_MEMBER)
        if raw_proof is None:
            return
        proof = plan_object(raw_proof, "mfaFactorProof")
        claim_path = plan_string(proof.get("claim"), "mfaFactorProof.claim")
        proving_values = {
            plan_string(value, "mfaFactorProof.provingValues[]")
            for value in plan_list(
                proof.get("provingValues"), "mfaFactorProof.provingValues"
            )
        }

        def proves(source_claims: Mapping[str, object]) -> bool:
            methods = _resolve_claim_path(dict(source_claims), claim_path)
            return isinstance(methods, list) and any(
                isinstance(method, str) and method in proving_values
                for method in methods
            )

        if proof.get(_PROOF_SOURCE_MEMBER) == _PROOF_SOURCE_INTROSPECTION:
            if await self._introspection_proves(
                token, claims, provider_name, provider, proof, proves
            ):
                return
        elif proves(claims):
            return
        logger.warning(
            "identity_auth_failed reason_code=%s claim=%s provider=%s",
            self._reasons.mfa_required,
            claim_path,
            provider_name,
        )
        raise JwksValidationError(
            reason_code=self._reasons.mfa_required,
            message=(
                "The verified token for provider '%s' proves no second factor: its '%s' "
                "claim lists none of %s.  The provider requires multi-factor sign-in."
                % (provider_name, claim_path, sorted(proving_values))
            ),
        )

    async def _introspection_proves(
        self,
        token: str,
        claims: dict[str, object],
        provider_name: str,
        provider: dict[str, object],
        proof: dict[str, object],
        proves: Callable[[Mapping[str, object]], bool],
    ) -> bool:
        """Ask the provider whether the session behind *token* completed a second factor.

        The provider's answer is its own record of the session, so the proof is the
        provider's, not a claim a service re-derives. An answer that cannot be obtained
        proves nothing (logged apart from a refusal, so an outage is not read as an
        attack), and the caller refuses the token either way.

        Returns:
            ``True`` when the answer is an active one about this token's subject whose
            authentication methods hold a proving value.

        Raises:
            RuntimeError: The entry's ``introspection`` object is malformed.
        """
        endpoint = plan_object(
            proof.get(_PROOF_INTROSPECTION_MEMBER), "mfaFactorProof.introspection"
        )
        try:
            return await self._factor_introspection.proves(
                token=token,
                claims=claims,
                issuer=plan_string(provider.get("issuer"), "issuer"),
                endpoint=endpoint,
                proving=proves,
            )
        except FactorIntrospectionUnavailable as problem:
            logger.error(
                "identity_mfa_introspection_unavailable provider=%s problem=%s",
                provider_name,
                problem,
            )
            return False

    def declared_identity(
        self, claims: dict[str, object], provider_name: str
    ) -> dict[str, object]:
        """The verified claims as ``Auth.identity`` reads them.

        A declared field is read through its claim path, so ``fullName`` mapped to
        ``name`` holds the token's ``name``. A field the token does not carry is
        ``None``, even when the token holds a claim spelled like the field: only the
        provider's declaration says what the field means. Every other claim keeps its
        own name.

        Args:
            claims: The verified claims of a token *provider_name* issued.
            provider_name: Logical provider name the token is attributed to.

        Returns:
            A new mapping; *claims* is left as verified.

        Raises:
            KeyError: *provider_name* is absent from the plan.
            RuntimeError: The plan cannot be loaded or an entry is malformed.
        """
        provider = plan_provider_entry(self.load_provider_plan(), provider_name)
        attribute_mappings = plan_object(
            provider.get("attributeMappings", {}), "attributeMappings"
        )
        identity = dict(claims)
        for field_name, raw_field_cfg in attribute_mappings.items():
            where = "attributeMappings.%s" % field_name
            claim_path = plan_string(
                plan_object(raw_field_cfg, where)["claimPath"], "%s.claimPath" % where
            )
            identity[field_name] = _resolve_claim_path(claims, claim_path)
        return identity
