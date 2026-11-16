"""Application settings assembled at startup. Auto-generated. Do not edit.

Assembled from baked bootstrap constants, config-store values, and resolved
secrets at service startup.  All connection strings are composed here from
non-secret parts (host/port/db from the config store ``connections``
namespace) and credential parts (password from the secrets backend).

The only environment reads in this module are the deploy-time application settings
the deployment delivers (via ``_require_env`` / ``_optional_env``): runtime facts that
exist only once the deployment has run -- the trusted-caller settings (Azure runtime
path + managed gateway), a shared cache identity's client id, a push platform
application's ARN, a CDN distribution's id. They are static for the deployment's
lifetime. A service that only CALLS peers reads the audience alone; the issuer and
trusted-principal allowlist are read only by a service that validates inbound callers.
Every other field is read from the config store or the secrets backend, never the
environment.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping

from cityservices_facility_service.config import _bootstrap

# ---------------------------------------------------------------------------
# Baked security / middleware constants (authored from service config at
# code-generation time; no environment reads).
# ---------------------------------------------------------------------------
DEBUG: bool = False
ALLOWED_HOSTS: list[str] = [
    "cityservices-facility-service",
    "localhost",
    "*.awsapprunner.com",
    "cityservices-facility-service.cityservices.System.local",
]
CORS_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:4300"]
CORS_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_HEADERS: list[str] = ["Authorization", "Content-Type"]
# Response headers a cross-origin caller may read beyond the CORS-safelisted ones:
# the ones the generated clients read (a rate-limited answer's Retry-After).
CORS_EXPOSE_HEADERS: list[str] = ["Retry-After"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service configuration readable from DSL logic via Config.get/getInt/getBool.
#
# Baked from the RESOLVED per-profile service config at generation time, under
# the same flat key shape the Config.* builtins compute (the DSL key
# lowercased, dots replaced by underscores). Only sections declared readable
# are present -- infrastructure blocks, the logical-secret table, and peer /
# integration wiring are deliberately absent, because their values are
# connection material and secret handles and must not appear as literals here.
# ---------------------------------------------------------------------------
CONFIG_VALUES: Final[Mapping[str, object]] = MappingProxyType(
    {
        "environment": "development",
        "profile": "development",
        "provider": "aws",
        "region": "us-east-1",
        "remoteconfigops_appconfigminpollseconds": 15,
    }
)


# ---------------------------------------------------------------------------
# Config-key resolution
# ---------------------------------------------------------------------------
# Inlined from cruftfree_codegen_python/runtime/config_values.py. A pure function
# of the mapping above -- so the generator's own suite tests its fail-loud
# behaviour by calling it, rather than by executing this rendered module.
class _ConfigKeyRequired:
    """Sentinel: the DSL call supplied no default, so absence is an error."""


#: Default marker for :func:`resolve_config_value`. A distinct sentinel rather
#: than ``None``: ``None`` is a legitimate configured value and a legitimate
#: DSL-supplied default, so using it here would make "no default given" and
#: "default is null" indistinguishable.
CONFIG_REQUIRED: type[_ConfigKeyRequired] = _ConfigKeyRequired


def config_key_lookup(key: str) -> str:
    """The flat lookup name for a DSL config key.

    Mirrors what the ``Config.*`` builtins compute at generation time -- the DSL
    key lowercased, dots replaced by underscores -- so the name a call site asks
    for is the name the baked mapping carries.

    Args:
        key: The config key exactly as written in the DSL.

    Returns:
        The flat key.
    """
    return key.replace(".", "_").lower()


def resolve_config_value(
    config_values: Mapping[str, object],
    key: str,
    default: object = CONFIG_REQUIRED,
) -> object:
    """Return the configured value for *key*, or *default* when one was given.

    Args:
        config_values: The values baked into this service at generation time.
        key: The config key exactly as written in the DSL, e.g.
            ``"validationReport.baseUrl"``.
        default: The default the DSL supplied. Absent means the DSL supplied
            none, and a missing key is then an error rather than a null.

    Returns:
        The configured value, or *default*.

    Raises:
        RuntimeError: When *key* is not configured and the DSL supplied no
            default. Failing here is the point -- see the module docstring.
    """
    lookup = config_key_lookup(key)
    if lookup in config_values:
        return config_values[lookup]
    if default is not CONFIG_REQUIRED:
        return default
    raise RuntimeError(
        f"Config key {key!r} is not configured for this service. "
        f"Configured keys: {sorted(config_values)}. "
        "Declare it in this service's .ccfg, or pass an explicit default at "
        "the call site to state that its absence is expected."
    )


_CONFIG_REQUIRED: Final[type[_ConfigKeyRequired]] = CONFIG_REQUIRED


def config_value(key: str, default: object = CONFIG_REQUIRED) -> object:
    """Return this service's configured value for *key*.

    Binds the baked ``CONFIG_VALUES`` to the shared resolver; see
    :func:`resolve_config_value` for the contract.
    """
    return resolve_config_value(CONFIG_VALUES, key, default)


def _require_env(name: str) -> str:
    """Return a required deploy-time app-setting value; raise if absent/empty.

    Covers the app settings the deployment itself produces and delivers to every
    host of this service (the trusted-caller settings: audience client id, expected
    issuer, trusted principal-id allowlist; the shared-UAI Redis credential's client
    id), static for the deployment's lifetime (no config-store/secrets-backend round
    trip). A missing or empty value here is a deployment wiring bug, never a valid
    "disabled" state.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required app setting {name!r} is missing or empty. "
            "This value is delivered as an application setting by the deployment. "
            "Verify the deployment wired this app setting before startup."
        )
    return value


@dataclass(frozen=True)
class AppSettings:
    """Frozen application settings assembled at startup.

    Fields are populated once during the lifespan ``startup`` phase via
    :func:`assemble_settings`.  No import-time construction occurs; any module
    that needs settings must call :func:`get_settings` after startup has run.
    """

    app_name: str
    environment: str
    host: str
    port: int
    facility_db_host: str
    facility_db_port: int
    facility_db_database: str
    facility_db_user: str
    facility_db_async_driver: str
    facility_db_password_handle: str
    trusted_caller_audience: str
    trusted_caller_issuer: str
    trusted_caller_principal_ids: str


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Return the assembled AppSettings.  Raises if called before startup."""
    if _settings is None:
        raise RuntimeError(
            "AppSettings have not been assembled yet. "
            "Call assemble_settings() during the lifespan startup phase before "
            "accessing settings. Ensure the startup lifespan handler runs before "
            "any request handler or background task that calls get_settings()."
        )
    return _settings


async def assemble_settings(
    config_client: object,
    secrets: object,
) -> AppSettings:
    """Assemble AppSettings from bootstrap, config store, and secrets.

    Fails loud (raises ``RuntimeError``) when any required namespace key or
    secret handle is absent.  No environment variables are read.

    Args:
        config_client: ``RemoteConfigClient`` instance (from ``config.remote_config``).
        secrets: ``_secrets_resolver`` module for resolving secret handles.

    Returns:
        Populated :class:`AppSettings` instance.

    Raises:
        RuntimeError: When a required config-store key or secret is absent.
    """
    from cityservices_facility_service.config.remote_config import ConnectionsKeys

    _facility_db_host = config_client.get_string(
        ConnectionsKeys.NAMESPACE, ConnectionsKeys.FACILITY_DB_HOST
    )
    _facility_db_port = config_client.get_int(
        ConnectionsKeys.NAMESPACE, ConnectionsKeys.FACILITY_DB_PORT
    )
    _facility_db_database = config_client.get_string(
        ConnectionsKeys.NAMESPACE, ConnectionsKeys.FACILITY_DB_DATABASE
    )
    _facility_db_user = config_client.get_string(
        ConnectionsKeys.NAMESPACE, ConnectionsKeys.FACILITY_DB_USER
    )
    _trusted_caller_audience = _require_env("CRUFTFREE_CALLER_AUDIENCE")
    _trusted_caller_issuer = _require_env("CRUFTFREE_CALLER_EXPECTED_ISSUER")
    _trusted_caller_principal_ids = _require_env(
        "CRUFTFREE_CALLER_TRUSTED_PRINCIPAL_IDS"
    )

    global _settings
    _settings = AppSettings(
        app_name=_bootstrap.PROFILE + "-cityservices_facility_service",
        environment=_bootstrap.PROFILE,
        host="0.0.0.0",
        port=8002,
        facility_db_host=_facility_db_host,
        facility_db_port=_facility_db_port,
        facility_db_database=_facility_db_database,
        facility_db_user=_facility_db_user,
        facility_db_async_driver="postgresql+asyncpg",
        facility_db_password_handle="facility_db_password",
        trusted_caller_audience=_trusted_caller_audience,
        trusted_caller_issuer=_trusted_caller_issuer,
        trusted_caller_principal_ids=_trusted_caller_principal_ids,
    )
    logger.info("app_settings_assembled environment=%s", _bootstrap.PROFILE)
    return _settings
