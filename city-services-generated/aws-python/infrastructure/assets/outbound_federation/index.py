"""Custom resource: the account's outbound identity federation, and its token issuer.

A trusted-caller token is an STS web identity token, which a role can request only once
outbound identity federation is enabled for the account. On create and update this
function enables it (an account that already has it enabled answers ``FeatureEnabled``,
which is accepted: the feature is account-wide, and another deployment may have turned
it on) and reads back the account's issuer, which every service verifies tokens against.
On delete it does nothing: disabling the feature would break every other workload in the
account that relies on it.

Two entry points carry the same outcome. ``handler`` returns it to the CDK ``Provider``
framework; ``cfn_handler`` is the function CloudFormation invokes directly as the
resource's service token, and sends it to the pre-signed response URL over HTTPS only. A
failure is reported with a reason naming the refused call, never a value.

Bundled with the boto3 release that carries these operations, so it never depends on
the SDK a Lambda runtime happens to ship. It logs the request type and outcome only.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Final

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SUCCESS: Final[str] = "SUCCESS"
_FAILED: Final[str] = "FAILED"
_HTTPS: Final[str] = "https"
_RESPONSE_HOST_SUFFIXES: Final[tuple[str, ...]] = (
    ".amazonaws.com",
    ".amazonaws.com.cn",
)
_RESPONSE_TIMEOUT_SECONDS: Final[int] = 30
_REASON_LIMIT: Final[int] = 2048


def _response_url(event: Mapping[str, object]) -> str:
    """The pre-signed response URL, refused unless it is an HTTPS URL under an AWS host."""
    url = event["ResponseURL"] if "ResponseURL" in event else None
    if not isinstance(url, str):
        raise RuntimeError("The request carries no ResponseURL.")
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme != _HTTPS or not host.endswith(_RESPONSE_HOST_SUFFIXES):
        raise RuntimeError(
            "The request's ResponseURL is not an HTTPS URL under an AWS host."
        )
    return url


def _respond(
    event: Mapping[str, object],
    status: str,
    reason: str,
    physical_resource_id: str,
    data: Mapping[str, str],
) -> None:
    """PUT the outcome to CloudFormation's pre-signed URL (certificate verified).

    ``data`` becomes the resource's attributes; an empty mapping sends none.
    """
    url = _response_url(event)
    outcome: dict[str, object] = {
        "Status": status,
        "Reason": reason[:_REASON_LIMIT],
        "PhysicalResourceId": physical_resource_id,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
    }
    if data:
        outcome["Data"] = dict(data)
    body = json.dumps(outcome).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={"Content-Type": "", "Content-Length": str(len(body))},
    )
    with urllib.request.urlopen(request, timeout=_RESPONSE_TIMEOUT_SECONDS) as response:
        logger.info(
            "custom_resource_response status=%s http=%d", status, response.status
        )


#: The response field and custom-resource attribute carrying the issuer.
_ISSUER_FIELD = "IssuerIdentifier"
#: The physical id a failed create reports: there is no issuer to name it by.
_FAILED_PHYSICAL_RESOURCE_ID: Final[str] = "outbound-web-identity-federation"
_CREATE: Final[str] = "Create"
_UPDATE: Final[str] = "Update"
_DELETE: Final[str] = "Delete"


def _issuer() -> str:
    """Enable outbound identity federation (idempotently) and return the account issuer.

    Raises:
        RuntimeError: IAM reports no issuer once the feature is enabled.
    """
    iam = boto3.client("iam")
    try:
        iam.enable_outbound_web_identity_federation()
        logger.info("outbound_web_identity_federation_enabled")
    except iam.exceptions.FeatureEnabledException:
        logger.info("outbound_web_identity_federation_already_enabled")
    issuer = iam.get_outbound_web_identity_federation_info()[_ISSUER_FIELD]
    if not isinstance(issuer, str) or not issuer.startswith("https://"):
        raise RuntimeError(
            "IAM returned no https token issuer for the account after enabling outbound "
            "identity federation; trusted-caller tokens cannot be verified without it."
        )
    return issuer


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    """CloudFormation custom-resource event handler (CDK ``Provider`` framework)."""
    del context
    request_type = event["RequestType"] if "RequestType" in event else None
    logger.info("outbound_federation_request type=%s", request_type)
    if request_type == _DELETE:
        return {"PhysicalResourceId": event["PhysicalResourceId"]}
    issuer = _issuer()
    return {"PhysicalResourceId": issuer, "Data": {_ISSUER_FIELD: issuer}}


def _current_physical_id(event: Mapping[str, object]) -> str:
    """The id CloudFormation already holds for the resource, or the failed-create id."""
    current = event["PhysicalResourceId"] if "PhysicalResourceId" in event else None
    return (
        current
        if isinstance(current, str) and current
        else _FAILED_PHYSICAL_RESOURCE_ID
    )


def _failure_reason(error: Exception) -> str:
    """The reason a failed request reports: the refused call or the unmet requirement."""
    if isinstance(error, ClientError):
        code = error.response["Error"]["Code"]
        logger.error(
            "outbound_federation FAILED: AWS refused %s (%s)",
            error.operation_name,
            code,
        )
        return "AWS refused %s (%s); see the function's log group." % (
            error.operation_name,
            code,
        )
    if isinstance(error, RuntimeError):
        logger.error("outbound_federation FAILED: %s", error)
        return str(error)
    logger.exception("outbound_federation FAILED: unexpected error")
    return "Enabling outbound identity federation failed unexpectedly; see the function's log group."


def cfn_handler(event: Mapping[str, object], context: object) -> None:
    """CloudFormation custom-resource event handler (invoked directly by the stack)."""
    del context
    request_type = event["RequestType"] if "RequestType" in event else None
    logger.info("outbound_federation_request type=%s", request_type)
    if request_type == _DELETE:
        reason = "Delete leaves the account-wide outbound identity federation enabled."
        _respond(event, _SUCCESS, reason, _current_physical_id(event), {})
        return
    try:
        if request_type not in (_CREATE, _UPDATE):
            raise RuntimeError("Unsupported request type %r." % request_type)
        issuer = _issuer()
    except (
        Exception
    ) as error:  # every fault still answers CloudFormation, which would wait otherwise
        _respond(
            event, _FAILED, _failure_reason(error), _current_physical_id(event), {}
        )
        return
    reason = "Outbound identity federation is enabled."
    _respond(event, _SUCCESS, reason, issuer, {_ISSUER_FIELD: issuer})
