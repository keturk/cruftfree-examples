"""Identity validation for helpdesk.TicketService.

Binds the JWKS token-validation core (``_runtime/identity_core``) to this
service: its reason codes, its bootstrap module (which locates the identity
provider plan) and the plan schema version it was generated for.
"""

from __future__ import annotations

from helpdesk_ticket_service._runtime.identity_core import (
    IdentityCore,
    IdentityReasons,
    JwksValidationError,
    plan_object,
    plan_providers,
)
from helpdesk_ticket_service.config import _bootstrap

# Reason codes -- rendered from the shared AuthReasonCode vocabulary. Logged,
# never returned to a caller.
_REASON_MISSING_TOKEN: str = "missing_token"
_REASON_MALFORMED_TOKEN: str = "malformed_token"
_REASON_EXPIRED_TOKEN: str = "expired_token"
_REASON_BAD_SIGNATURE: str = "bad_signature"
_REASON_ISSUER_MISMATCH: str = "issuer_mismatch"
_REASON_AUDIENCE_MISMATCH: str = "audience_mismatch"
_REASON_PROVIDER_MISMATCH: str = "provider_mismatch"
_REASON_JWKS_REFRESH_FAILED: str = "jwks_refresh_failed"
_REASON_PROVIDER_CONFIG: str = "provider_config_error"
_REASON_REQUIRED_FIELD_MISSING: str = "required_identity_field_missing"
_REASON_MFA_REQUIRED: str = "mfa_required"

_core = IdentityCore(
    reasons=IdentityReasons(
        malformed_token=_REASON_MALFORMED_TOKEN,
        expired_token=_REASON_EXPIRED_TOKEN,
        bad_signature=_REASON_BAD_SIGNATURE,
        issuer_mismatch=_REASON_ISSUER_MISMATCH,
        audience_mismatch=_REASON_AUDIENCE_MISMATCH,
        provider_mismatch=_REASON_PROVIDER_MISMATCH,
        jwks_refresh_failed=_REASON_JWKS_REFRESH_FAILED,
        provider_config=_REASON_PROVIDER_CONFIG,
        required_field_missing=_REASON_REQUIRED_FIELD_MISSING,
        mfa_required=_REASON_MFA_REQUIRED,
    ),
    bootstrap=_bootstrap,
    plan_schema_version=8,
)

validate_token_claims = _core.validate_token_claims
load_provider_plan = _core.load_provider_plan
resolve_provider_name = _core.resolve_provider_name
local_user_id = _core.local_user_id
declared_identity = _core.declared_identity
clear_identity_caches = _core.clear_caches

__all__ = [
    "JwksValidationError",
    "clear_identity_caches",
    "declared_identity",
    "load_provider_plan",
    "local_user_id",
    "plan_object",
    "plan_providers",
    "resolve_provider_name",
    "validate_token_claims",
]
