"""Azure managed identity as a generated service's machine identity.

Emitted verbatim as ``<package>/_runtime/service_credential_managed_identity.py``
beside ``service_credential_core`` for a service whose platform's
machine-identity strategy is ``managed-identity``.

The token is minted for the machine identity provider's audience -- its Entra
app-registration client-ID GUID, delivered as a deploy-time app setting. The
callee's route chain validates the service credential's ``aud`` against this
SAME provider audience, so the token MUST be minted for it -- never for the
callee's network base URL, which is not a registered OAuth resource (requesting
``{base_url}/.default`` yields AADSTS500011).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol

#: Suffix of the scope requested for a resource's application permissions.
_DEFAULT_SCOPE_SUFFIX: str = "/.default"


class AccessToken(Protocol):
    """The token a credential answers with."""

    @property
    def token(self) -> str: ...


class AsyncTokenCredential(Protocol):
    """The async managed-identity credential the service's ``config._credentials`` builds."""

    async def get_token(self, *scopes: str) -> AccessToken: ...


class ManagedIdentityCredential:
    """Mints the managed-identity token one outbound call presents.

    Args:
        credential_factory: Builds the service's managed-identity credential
            (``config._credentials.azure_credential``), which never consults
            environment variables.
        audience_env_var: The app setting carrying the machine provider's audience;
            the provider plan's ``allowedAudienceRefs`` names the same setting, so
            the requested and validated audiences are the one value.
    """

    def __init__(
        self,
        *,
        credential_factory: Callable[[], AsyncTokenCredential],
        audience_env_var: str,
    ) -> None:
        self._credential_factory = credential_factory
        self._audience_env_var = audience_env_var

    def audience(self) -> str:
        """Return the machine provider's audience GUID from its deploy-time env var.

        Fails loud when unset: the credential cannot be minted for an unknown
        resource, and falling back to any other value (e.g. the callee's URL) is the
        exact conflation that produces AADSTS500011.

        Raises:
            RuntimeError: When the audience env var is unset or empty.
        """
        audience = os.environ.get(self._audience_env_var, "").strip()
        if not audience:
            raise RuntimeError(
                f"Machine-identity audience env var '{self._audience_env_var}' is "
                "unset or empty. It carries the machine identity provider's Entra "
                "client-ID GUID (a deploy-time ARM output delivered as an app setting); "
                "the service-to-service credential is minted for this resource. Ensure "
                "the identity audience app settings are wired by the platform deployer."
            )
        return audience

    async def mint(self) -> str:
        """Obtain the credential from the platform for the machine provider's audience."""
        credential = self._credential_factory()
        token = await credential.get_token(f"{self.audience()}{_DEFAULT_SCOPE_SUFFIX}")
        return token.token
