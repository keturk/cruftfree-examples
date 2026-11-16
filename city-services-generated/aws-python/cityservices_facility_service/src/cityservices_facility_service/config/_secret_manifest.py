"""Data-only secret reference manifest. Auto-generated. Do not edit.

Maps each logical secret handle to its rendered backend-specific name and
whether the secret is required.  Built once by the shared
``SecretReferenceManifest`` during code generation; consumed at runtime by
``secrets_resolver.py`` for all handle → name lookups.

No imports that perform I/O, read environment variables, or contact any SDK
are permitted in this module.  It is a pure data constant.
"""

from __future__ import annotations

# Backend selected at generation time from SecretBackendPolicy.default_backend.
SECRET_BACKEND: str = "aws-secrets-manager"

# Default cache TTL (seconds) baked from SecretBackendPolicy.default_secret_ttl_seconds.
# Applied to a handle whose entry omits ``ttl_seconds``. 0 means "no expiry".
DEFAULT_SECRET_TTL_SECONDS: int = 300

# Mapping from logical handle → {rendered_name, required, ttl_seconds, store_endpoint,
# provisioning_authority}.
# rendered_name: the backend-specific secret name / path / filename.
# required: when True, an absent secret is a hard runtime failure.
# ttl_seconds: per-handle cache TTL; 0 means "no expiry, cache for process lifetime".
# store_endpoint: the URL of the store holding the secret (azure-key-vault only; None
#   for every other backend).
# provisioning_authority: "operator", "cruftfree" or "platform-iac"; metadata only, never a value.
SECRET_REFERENCES: dict[str, dict[str, object]] = {
    "facility_db_password": {
        "rendered_name": "cityservices-facility-service/cityservices_facility_service_facility_db_rw_password",
        "required": True,
        "ttl_seconds": 300,
        "store_endpoint": None,
        "provisioning_authority": "platform-iac",
    },
}
