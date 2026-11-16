"""Managed machine-identity credential acquisition for inter-service calls.

Binds the bounded acquisition core (``_runtime/service_credential_core``) to this
service's machine-identity strategy. The credential is the platform's own machine
identity, never a self-signed application token and never a static shared secret.

Strategy: managed-identity
"""

from __future__ import annotations

from helpdesk_email_mock._runtime.service_credential_core import (
    BoundedServiceCredential,
    ServiceCredentialTimeout,
)
from helpdesk_email_mock._runtime.service_credential_managed_identity import (
    ManagedIdentityCredential,
)
from helpdesk_email_mock.config import _credentials

# The app setting delivering the machine provider's audience (its Entra client-ID GUID):
# the name cruftfree-codegen-azure's build_identity_audience_settings emits and the provider
# plan references in allowedAudienceRefs, so requested and validated audiences are one value.
_minter = ManagedIdentityCredential(
    credential_factory=_credentials.azure_credential,
    audience_env_var="IDENTITY_MACHINE_AUDIENCE_CLIENT_ID",
)


class ServiceCredentialTimeoutError(ServiceCredentialTimeout):
    """The machine-identity credential was not obtained within its bound."""


acquire_service_credential = BoundedServiceCredential(
    mint=_minter.mint,
    timeout_seconds=15.0,
    timeout_error=ServiceCredentialTimeoutError,
).acquire
