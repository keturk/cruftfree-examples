"""Secrets resolution by logical handle. Auto-generated. Do not edit.

Binds the resolution core (``_runtime/secret_resolver_core``) to this service's
secret manifest (``config._secret_manifest``: every handle's rendered backend
name, built at generation time) and to the docker-secret backend's
fetch, with the cache policy baked from ``SecretBackendPolicy``. No environment
variables are read at runtime.
"""

from __future__ import annotations

from cityservices_request_service._runtime.secret_backend_mounted_file import (
    MountedFileSecrets,
)
from cityservices_request_service._runtime.secret_resolver_core import (
    SecretReferences,
    SecretResolver,
)
from cityservices_request_service.config import _bootstrap, _secret_manifest

_references = SecretReferences(_secret_manifest.SECRET_REFERENCES)
_backend = MountedFileSecrets(_references, bootstrap=_bootstrap)

_resolver = SecretResolver(
    backend="docker-secret",
    references=_references,
    fetch=_backend.fetch,
    default_ttl_seconds=300,
    fail_closed_on_refresh=False,
    invalidation_throttle_seconds=1.0,
)

get_secret = _resolver.get_secret
invalidate_secret = _resolver.invalidate_secret
clear_secret_cache = _resolver.clear
