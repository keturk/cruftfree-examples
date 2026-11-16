"""Custom resource: the VPC's default security group, left with no rules.

EC2 creates the group admitting its own members and sending anywhere, and CloudFormation
cannot edit its rules. On create and update this function reads the group and revokes
every ingress and egress permission it holds, so an interface placed in the VPC without
a group of its own can neither receive nor send. A refused revoke fails the stack. On
delete it does nothing: the group goes away with the VPC.

CloudFormation invokes ``cfn_handler`` directly as the resource's service token, and the
outcome goes to the pre-signed response URL over HTTPS only. A failure is reported with a
reason naming the refused call, never a value. It logs the request type and the number of
revoked permissions only.
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
_RESPONSE_HOST_SUFFIXES: Final[tuple[str, ...]] = ('.amazonaws.com', '.amazonaws.com.cn')
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
        raise RuntimeError("The request's ResponseURL is not an HTTPS URL under an AWS host.")
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
        url, data=body, method="PUT", headers={"Content-Type": "", "Content-Length": str(len(body))}
    )
    with urllib.request.urlopen(request, timeout=_RESPONSE_TIMEOUT_SECONDS) as response:
        logger.info("custom_resource_response status=%s http=%d", status, response.status)

#: The custom-resource property naming the group.
_GROUP_ID_PROPERTY: Final[str] = "GroupId"
#: The physical id a failed create reports: no group was read to name it by.
_FAILED_PHYSICAL_RESOURCE_ID: Final[str] = "default-security-group-closed"
_CREATE: Final[str] = "Create"
_UPDATE: Final[str] = "Update"
_DELETE: Final[str] = "Delete"


def _group_id(event: Mapping[str, object]) -> str:
    """The group the request names.

    Raises:
        RuntimeError: the request names no group.
    """
    properties = event["ResourceProperties"] if "ResourceProperties" in event else None
    group_id = (
        properties[_GROUP_ID_PROPERTY]
        if isinstance(properties, Mapping) and _GROUP_ID_PROPERTY in properties
        else None
    )
    if not isinstance(group_id, str) or not group_id:
        raise RuntimeError("The request names no security group in %s." % _GROUP_ID_PROPERTY)
    return group_id


def _close(group_id: str) -> None:
    """Revoke every ingress and egress permission ``group_id`` holds.

    Raises:
        RuntimeError: EC2 does not return exactly that group.
    """
    ec2 = boto3.client("ec2")
    groups = ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"]
    if len(groups) != 1:
        raise RuntimeError("EC2 returned %d groups for one group id." % len(groups))
    ingress = groups[0]["IpPermissions"]
    egress = groups[0]["IpPermissionsEgress"]
    if ingress:
        ec2.revoke_security_group_ingress(GroupId=group_id, IpPermissions=ingress)
    if egress:
        ec2.revoke_security_group_egress(GroupId=group_id, IpPermissions=egress)
    logger.info("default_group_closed ingress=%d egress=%d", len(ingress), len(egress))


def _current_physical_id(event: Mapping[str, object]) -> str:
    """The id CloudFormation already holds for the resource, or the failed-create id."""
    current = event["PhysicalResourceId"] if "PhysicalResourceId" in event else None
    return current if isinstance(current, str) and current else _FAILED_PHYSICAL_RESOURCE_ID


def _failure_reason(error: Exception) -> str:
    """The reason a failed request reports: the refused call or the unmet requirement."""
    if isinstance(error, ClientError):
        code = error.response["Error"]["Code"]
        logger.error("default_group FAILED: AWS refused %s (%s)", error.operation_name, code)
        return "AWS refused %s (%s); see the function's log group." % (error.operation_name, code)
    if isinstance(error, RuntimeError):
        logger.error("default_group FAILED: %s", error)
        return str(error)
    logger.exception("default_group FAILED: unexpected error")
    return "Closing the default security group failed unexpectedly; see the function's log group."


def cfn_handler(event: Mapping[str, object], context: object) -> None:
    """CloudFormation custom-resource event handler (invoked directly by the stack)."""
    del context
    request_type = event["RequestType"] if "RequestType" in event else None
    logger.info("default_group_request type=%s", request_type)
    if request_type == _DELETE:
        reason = "The default security group goes away with its VPC."
        _respond(event, _SUCCESS, reason, _current_physical_id(event), {})
        return
    try:
        if request_type not in (_CREATE, _UPDATE):
            raise RuntimeError("Unsupported request type %r." % request_type)
        group_id = _group_id(event)
        _close(group_id)
    except Exception as error:  # every fault still answers CloudFormation, which would wait otherwise
        _respond(event, _FAILED, _failure_reason(error), _current_physical_id(event), {})
        return
    _respond(event, _SUCCESS, "The default security group holds no rules.", group_id, {})
