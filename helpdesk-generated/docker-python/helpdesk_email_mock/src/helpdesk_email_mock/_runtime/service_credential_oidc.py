"""OIDC client-credentials machine tokens as a generated service's machine identity.

Emitted verbatim as ``<package>/_runtime/service_credential_oidc.py`` beside
``service_credential_core`` for a service whose platform's machine-identity
strategy is ``oidc-client-credentials`` (Docker/self-host): the platform machine
identity is a Zitadel service account.

The provisioning init-job mints the machine service account and writes its
credentials to a file on a shared volume, mounted read-only into every service;
services depend on the init-job completing, so the file is present before the
first inter-service call. The client id and secret are exchanged for an RS256
access token through the OAuth2 ``client_credentials`` grant, cached per
requested audience until shortly before its ``exp``.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# Required keys in the credentials file. ``audience`` is the reserved Zitadel
# project-audience scope (``urn:zitadel:iam:org:project:id:<projectId>:aud``) that
# places the machine project in the token's ``aud`` claim so the callee's JWKS
# guard accepts it. ``instanceOrigin`` is the Zitadel instance base URL,
# doubling as the Management-API base (``{instanceOrigin}/management/v1/...``)
# -- consumed by ``_provider_metadata.py``'s write-back client.
_REQUIRED_CREDENTIAL_KEYS: tuple[str, ...] = (
    "clientId",
    "clientSecret",
    "tokenUrl",
    "hostHeader",
    "audience",
    "instanceOrigin",
)

# Optional member: provider name -> the id of the organization holding that provider's users.
_ORGANIZATIONS_KEY: str = "organizations"

_HTTP_OK: int = 200
_JWT_SEGMENTS: int = 3
_BASE64_BLOCK: int = 4
_ERROR_BODY_EXCERPT_CHARS: int = 300
_NO_EXPIRY: float = 0.0


def _decode_token_expiry(token: str) -> float:
    """Return the JWT ``exp`` (epoch seconds), or ``0.0`` when it cannot be read."""
    parts = token.split(".")
    if len(parts) != _JWT_SEGMENTS:
        return _NO_EXPIRY
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % _BASE64_BLOCK)
    try:
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        claims: object = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return _NO_EXPIRY
    if not isinstance(claims, dict):
        return _NO_EXPIRY
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        return float(exp)
    return _NO_EXPIRY


class ClientCredentialsMachineTokens:
    """Machine tokens of the platform service account, cached per audience.

    Inter-service calls use the machine-project audience the callee's JWKS guard
    accepts (the empty-string key -> ``creds["audience"]``); a provider
    management-API write (``_provider_metadata.py``) uses that API's OWN reserved
    audience -- a DIFFERENT ``aud`` -- so each is cached under its own key and one
    never masks the other.

    Args:
        credentials_file: Where the init-job writes the machine credentials.
        token_expiry_skew_seconds: Refresh a cached token this many seconds before
            its real expiry, so an in-flight request never presents an
            already-expired token.
    """

    def __init__(
        self, *, credentials_file: str, token_expiry_skew_seconds: float
    ) -> None:
        self._credentials_file = credentials_file
        self._token_expiry_skew_seconds = token_expiry_skew_seconds
        self._token_lock = asyncio.Lock()
        self._cached_tokens: dict[str, tuple[str, float]] = {}

    def _read_document(self) -> dict[str, object]:
        """The machine credentials document the init-job wrote.

        Raises:
            RuntimeError: When the file is absent, unreadable or not a JSON object.
        """
        path = self._credentials_file
        try:
            with open(path, encoding="utf-8") as handle:
                raw: object = json.load(handle)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Machine credentials file '{path}' not found. "
                "The Zitadel provisioning init-job mints the machine service account "
                "and writes this file; ensure this service depends on that job and "
                "mounts the shared machine-credentials volume."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Machine credentials file '{path}' is not valid JSON: {exc}."
            ) from exc
        if not isinstance(raw, dict):
            raise RuntimeError(
                f"Machine credentials file '{path}' must contain a JSON object."
            )
        return raw

    def provider_organization(self, provider: str) -> str | None:
        """The organization id a provider's users live in, when it has an organization of its own.

        A provider that requires a second factor at sign-in has an organization of its
        own, and the init-job records its id under ``organizations``. Every other
        provider's users live in the instance's default organization, which no call
        needs to name.

        Returns:
            The provider's organization id, or ``None`` for a provider without one.

        Raises:
            RuntimeError: When the file is absent or unreadable, or ``organizations`` is
                present and is not an object of strings.
        """
        document = self._read_document()
        if _ORGANIZATIONS_KEY not in document:
            return None
        organizations = document[_ORGANIZATIONS_KEY]
        if not isinstance(organizations, dict) or not all(
            isinstance(key, str) and isinstance(value, str) and value
            for key, value in organizations.items()
        ):
            raise RuntimeError(
                f"Machine credentials file '{self._credentials_file}' holds an "
                f"'{_ORGANIZATIONS_KEY}' member that is not an object of organization ids. "
                "Regenerate and redeploy so the init-job rewrites the file."
            )
        return organizations.get(provider)

    def load_machine_credentials(self) -> dict[str, str]:
        """Return the Zitadel machine service-account credentials the init-job wrote.

        Returns:
            Mapping with ``clientId``, ``clientSecret``, ``tokenUrl``, ``hostHeader``,
            ``audience``, and ``instanceOrigin``.

        Raises:
            RuntimeError: When the file is absent, malformed, or missing a key.
        """
        path = self._credentials_file
        raw = self._read_document()
        creds: dict[str, str] = {}
        missing: list[str] = []
        for key in _REQUIRED_CREDENTIAL_KEYS:
            value = raw.get(key)
            if isinstance(value, str) and value:
                creds[key] = value
            else:
                missing.append(key)
        if missing:
            raise RuntimeError(
                f"Machine credentials file '{path}' is missing "
                f"required keys {missing}. Regenerate and redeploy so the init-job "
                "rewrites the file."
            )
        return creds

    def _cached(self, scope_audience: str) -> str | None:
        """The cached token for *scope_audience* while it is still fresh."""
        cached = self._cached_tokens.get(scope_audience)
        if (
            cached is not None
            and time.time() < cached[1] - self._token_expiry_skew_seconds
        ):
            return cached[0]
        return None

    async def acquire(self, scope_audience: str = "") -> str:
        """Return a cached or freshly minted Zitadel machine access token.

        Args:
            scope_audience: The client-credentials audience/scope to mint the token
                for. Empty (the default) means the machine-project audience baked in
                the credentials file (``creds["audience"]``) -- the inter-service
                audience the callee's JWKS guard accepts. A non-empty value (a
                provider management-API's own reserved audience) mints and caches a
                token scoped to THAT audience instead, without disturbing the
                inter-service token.

        Raises:
            RuntimeError: When the token endpoint rejects the request or returns no
                access token.
        """
        # Cache key is the requested scope verbatim -- "" for the default
        # machine-project token, the reserved audience for a provider management-API
        # token -- so the two never share a slot.
        cached = self._cached(scope_audience)
        if cached is not None:
            return cached
        async with self._token_lock:
            cached = self._cached(scope_audience)
            if cached is not None:
                return cached
            return await self._mint_token(scope_audience)

    async def _mint_token(self, scope_audience: str) -> str:
        creds = self.load_machine_credentials()
        audience = scope_audience or creds["audience"]
        form = {
            "grant_type": "client_credentials",
            "scope": f"openid {audience}",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                creds["tokenUrl"],
                data=form,
                auth=(creds["clientId"], creds["clientSecret"]),
                headers={"Host": creds["hostHeader"]},
            )
        if response.status_code != _HTTP_OK:
            raise RuntimeError(
                "Failed to acquire Zitadel machine token via client_credentials "
                f"(HTTP {response.status_code}): "
                f"{response.text[:_ERROR_BODY_EXCERPT_CHARS]}. "
                "Verify the machine service account exists and its secret matches "
                "the credentials file."
            )
        body: object = response.json()
        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise RuntimeError(
                "Zitadel token response did not contain an 'access_token'."
            )
        expires_in = body.get("expires_in") if isinstance(body, dict) else None
        fallback_expiry = time.time() + (
            float(expires_in) if isinstance(expires_in, (int, float)) else _NO_EXPIRY
        )
        expiry = _decode_token_expiry(token) or fallback_expiry
        self._cached_tokens[scope_audience] = (token, expiry)
        logger.debug(
            "zitadel_machine_token_acquired audience=%s expiry=%s", audience, expiry
        )
        return token

    async def mint(self) -> str:
        """The inter-service token: scoped to the machine project (baked in the credentials file)."""
        return await self.acquire()

    async def acquire_for_audience(self, audience: str) -> str:
        """Return a machine token scoped to a provider management-API's own audience.

        A provider's own management API gates on a DIFFERENT ``aud`` than sibling
        services do: sibling services accept the machine-project audience baked in
        the credentials file, but the provider management API accepts only its own
        reserved API audience. The write-back client (``_provider_metadata.py``)
        calls this with the platform-declared ``token_audience`` so the metadata
        write is authenticated against the management API, not a peer service.

        Args:
            audience: The reserved provider management-API audience/scope string
                (the platform's declared
                ``IdentityWriteBackDeclaration.token_audience``). An empty string
                falls back to the machine-project audience -- for a platform whose
                management API happens to accept the inter-service audience. Never a
                peer service's network address.

        Returns:
            The bearer token string scoped to ``audience``.

        Raises:
            RuntimeError: When the token endpoint rejects the request or returns no
                access token.
        """
        return await self.acquire(scope_audience=audience)
