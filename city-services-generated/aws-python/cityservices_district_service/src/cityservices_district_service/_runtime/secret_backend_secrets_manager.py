"""AWS Secrets Manager as a generated service's secret backend.

Emitted verbatim as ``<package>/_runtime/secret_backend_secrets_manager.py``
beside ``secret_resolver_core`` for a service whose secret backend is
``aws-secrets-manager``. The client comes from the service's
``config._credentials`` (instance-role credentials, baked region), so no
environment variable is consulted.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Protocol

from .secret_resolver_core import SecretReferences

#: The AWS service the client is built for.
SECRETS_MANAGER_SERVICE = "secretsmanager"

#: The error codes Secrets Manager answers for a secret that does not exist.
_NOT_FOUND_CODES = frozenset({"ResourceNotFoundException", "SecretNotFoundException"})

#: The response field carrying a string secret's value.
_SECRET_STRING_KEY = "SecretString"


class SecretsManagerClient(Protocol):
    """The part of a boto3 ``secretsmanager`` client the fetch calls."""

    def get_secret_value(self, **request: str) -> Mapping[str, object]:
        """Read one secret's current value (``SecretId`` names it)."""


class SecretsManagerSecrets:
    """Reads secrets from AWS Secrets Manager.

    Args:
        references: The service's secret manifest; a handle's rendered name is its
            secret name.
        client_factory: Builds a client for an AWS service name
            (``config._credentials.aws_client``).
    """

    def __init__(
        self,
        references: SecretReferences,
        *,
        client_factory: Callable[[str], SecretsManagerClient],
    ) -> None:
        self._references = references
        self._client_factory = client_factory

    async def fetch(self, handle: str) -> str | None:
        """The string value of *handle*'s secret.

        Returns:
            The secret string, or ``None`` when the secret does not exist or holds
            no string. Never logged.

        Raises:
            KeyError: *handle* is not declared in the manifest.
            ImportError: ``botocore`` is not installed.
            RuntimeError: Secrets Manager answered any other error; the message
                names the handle, the secret name and the error code.
        """
        secret_name = self._references.rendered_name(handle)
        try:
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise ImportError(
                "boto3/botocore is not installed. "
                "Add 'boto3>=1.34.0' to the service dependencies."
            ) from exc
        client = self._client_factory(SECRETS_MANAGER_SERVICE)
        try:
            response = await asyncio.to_thread(
                client.get_secret_value, SecretId=secret_name
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            if error_code in _NOT_FOUND_CODES:
                return None
            raise RuntimeError(
                "AWS Secrets Manager error for handle %r (name=%r): %s. "
                "Check IAM permissions and secret configuration."
                % (handle, secret_name, error_code)
            ) from exc
        if _SECRET_STRING_KEY not in response:
            return None
        return str(response[_SECRET_STRING_KEY])
