"""Managed machine-identity credential acquisition for inter-service calls.

Binds the bounded acquisition core (``_runtime/service_credential_core``) to this
service's machine-identity strategy. The credential is the platform's own machine
identity, never a self-signed application token and never a static shared secret.

Strategy: iam-role
"""

from __future__ import annotations

from cityservices_sms_mock._runtime.service_credential_core import (
    BoundedServiceCredential,
    ServiceCredentialTimeout,
)
from cityservices_sms_mock._runtime.service_credential_iam_role import (
    RoleSessionCredential,
)
from cityservices_sms_mock.config import _credentials

_minter = RoleSessionCredential(role_credentials=_credentials.aws_role_credentials)


class ServiceCredentialTimeoutError(ServiceCredentialTimeout):
    """The machine-identity credential was not obtained within its bound."""


acquire_service_credential = BoundedServiceCredential(
    mint=_minter.mint,
    timeout_seconds=15.0,
    timeout_error=ServiceCredentialTimeoutError,
).acquire
