"""Managed machine-identity credential acquisition for inter-service calls.

Binds the bounded acquisition core (``_runtime/service_credential_core``) to this
service's machine-identity strategy. The credential is the platform's own machine
identity, never a self-signed application token and never a static shared secret.

Strategy: oidc-client-credentials
"""

from __future__ import annotations

from cityservices_request_service._runtime.service_credential_core import (
    BoundedServiceCredential,
    ServiceCredentialTimeout,
)
from cityservices_request_service._runtime.service_credential_oidc import (
    ClientCredentialsMachineTokens,
)

# The Zitadel provisioning init-job writes the machine credentials here, on the shared
# read-only volume the platform mounts (cruftfree_common.identity.machine_credentials).
_minter = ClientCredentialsMachineTokens(
    credentials_file="/machine-credentials/credentials.json",
    token_expiry_skew_seconds=30.0,
)
_load_machine_credentials = _minter.load_machine_credentials
provider_organization_id = _minter.provider_organization
acquire_provider_metadata_credential = _minter.acquire_for_audience


class ServiceCredentialTimeoutError(ServiceCredentialTimeout):
    """The machine-identity credential was not obtained within its bound."""


acquire_service_credential = BoundedServiceCredential(
    mint=_minter.mint,
    timeout_seconds=15.0,
    timeout_error=ServiceCredentialTimeoutError,
).acquire
