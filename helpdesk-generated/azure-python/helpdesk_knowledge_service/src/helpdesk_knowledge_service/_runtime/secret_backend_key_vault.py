"""Azure Key Vault as a generated service's secret backend.

Emitted verbatim as ``<package>/_runtime/secret_backend_key_vault.py`` beside
``secret_resolver_core`` for a service whose secret backend is
``azure-key-vault``. Each secret is read from the vault the application placement
gave it, with the managed-identity credential of the service's
``config._credentials``, so no environment variable is consulted.
"""

from __future__ import annotations

from collections.abc import Callable

from .secret_resolver_core import SecretReferences


class KeyVaultSecrets:
    """Reads secrets from Azure Key Vault.

    Args:
        references: The service's secret manifest; a handle's rendered name is its
            Key Vault secret name (already normalised for Key Vault at generation
            time) and its store endpoint is the vault URL.
        credential_factory: Builds the async managed-identity credential
            (``config._credentials.azure_credential``).
    """

    def __init__(
        self, references: SecretReferences, *, credential_factory: Callable[[], object]
    ) -> None:
        self._references = references
        self._credential_factory = credential_factory

    async def fetch(self, handle: str) -> str | None:
        """The value of *handle*'s secret in its vault.

        Returns:
            The secret value, or ``None`` when the secret does not exist. Never logged.

        Raises:
            KeyError: *handle* is not declared in the manifest.
            ImportError: ``azure-keyvault-secrets`` / ``azure-identity`` are absent.
        """
        kv_name = self._references.rendered_name(handle)
        vault_url = self._references.store_endpoint(handle)
        try:
            from azure.core.exceptions import ResourceNotFoundError
            from azure.keyvault.secrets.aio import SecretClient
        except ImportError as exc:
            raise ImportError(
                "azure-keyvault-secrets is not installed. "
                "Add 'azure-keyvault-secrets>=4.8.0' and 'azure-identity>=1.18.0' "
                "to the service dependencies."
            ) from exc
        credential = self._credential_factory()
        async with SecretClient(
            vault_url=vault_url,
            credential=credential,  # type: ignore[arg-type]
        ) as client:
            try:
                secret = await client.get_secret(kv_name)
            except ResourceNotFoundError:
                return None
        return secret.value
