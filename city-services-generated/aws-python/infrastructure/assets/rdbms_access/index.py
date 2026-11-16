"""Custom resource: the database access plan of a provisioned database.

Each database the stack provisions has an access plan: its owner, and a login of its own
for every service that writes or reads it. This function realizes the plan inside the
VPC, connected as the database's master login (the plan's owner), on create and on every
update:

* every login of the plan is created when absent and its password re-asserted from its
  own secret;
* the plan's grants are run as rendered at generation (``_BLOCKS``): the schema handed to
  the owner, ``CREATE`` on it revoked from ``PUBLIC``, and each login granted exactly its
  rights, on what exists and, through the owner's default privileges, on what it creates
  later.

The resource names its block and carries only the database's endpoint and the secrets'
ARNs; every statement comes from this module's table, never from the request, and a
block or a login set the table does not name is refused. Identifiers are composed by
``psycopg.sql`` and passwords passed as ``sql.Literal`` (PostgreSQL's role statements take
no bind parameters). Every credential is read from Secrets Manager at run time and never
logged. The connection takes the TLS the table names, the block's schema client's: the
server certificate and host name verified against the RDS CA bundle shipped beside this
module; for a block on an external server, the TLS the block declares. It logs the request
type and outcome only.

Idempotent: run again, it changes nothing. On delete it does nothing: the database is
retained or snapshotted with its stack, and dropping a login other sessions hold would
fail them.

Two entry points carry the same outcome. ``handler`` returns it to the CDK ``Provider``
framework; ``cfn_handler`` is the function CloudFormation invokes directly as the
resource's service token, and sends it to the pre-signed response URL over HTTPS only. A
failure is reported by the kind of error alone, never a value or a statement.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Final

import boto3
import psycopg
from psycopg import sql

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


_CREATE: Final[str] = "Create"
_UPDATE: Final[str] = "Update"
_DELETE: Final[str] = "Delete"
#: The physical id a create that failed before reading its properties reports.
_FAILED_PHYSICAL_RESOURCE_ID: Final[str] = "rdbms-access"
_CONNECT_TIMEOUT_SECONDS: Final[int] = 30
#: The file name the table gives the RDS CA bundle by.
_CA_BUNDLE_FILE: Final[str] = "rds-global-bundle.pem"
#: The RDS CA bundle bundled beside this module at synthesis.
_CA_BUNDLE: Final[str] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), _CA_BUNDLE_FILE
)
#: Per block: its database, its owner login, whether its server is external, the logins of
#: its plan, the statements that create a login and set its password, the plan's grants, and
#: the TLS its schema client connects with, rendered at generation.
_BLOCKS: Final[dict[str, dict[str, object]]] = json.loads(
    '{"cityservices.DistrictService.districtDb": {"administrator": "cruftfree_admin", "create_login": "CREATE ROLE {login} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "database": "cityservices_district", "external": false, "logins": ["cityservices_district_service_district_db_rw"], "set_password": "ALTER ROLE {login} WITH LOGIN PASSWORD {password}", "ssl_mode": "verify-full", "ssl_root": "rds-global-bundle.pem", "statements": ["CREATE SCHEMA IF NOT EXISTS \\"public\\" AUTHORIZATION \\"cruftfree_admin\\";", "ALTER SCHEMA \\"public\\" OWNER TO \\"cruftfree_admin\\";", "REVOKE CREATE ON SCHEMA \\"public\\" FROM PUBLIC;", "REVOKE CONNECT, TEMPORARY ON DATABASE \\"cityservices_district\\" FROM PUBLIC;", "GRANT CONNECT ON DATABASE \\"cityservices_district\\" TO \\"cruftfree_admin\\";", "GRANT CONNECT ON DATABASE \\"cityservices_district\\" TO \\"cityservices_district_service_district_db_rw\\";", "GRANT USAGE ON SCHEMA \\"public\\" TO \\"cityservices_district_service_district_db_rw\\";", "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA \\"public\\" TO \\"cityservices_district_service_district_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \\"cityservices_district_service_district_db_rw\\";", "GRANT USAGE ON ALL SEQUENCES IN SCHEMA \\"public\\" TO \\"cityservices_district_service_district_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT USAGE ON SEQUENCES TO \\"cityservices_district_service_district_db_rw\\";"]}, "cityservices.FacilityService.facilityDb": {"administrator": "cruftfree_admin", "create_login": "CREATE ROLE {login} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "database": "cityservices_facility", "external": false, "logins": ["cityservices_facility_service_facility_db_rw"], "set_password": "ALTER ROLE {login} WITH LOGIN PASSWORD {password}", "ssl_mode": "verify-full", "ssl_root": "rds-global-bundle.pem", "statements": ["CREATE SCHEMA IF NOT EXISTS \\"public\\" AUTHORIZATION \\"cruftfree_admin\\";", "ALTER SCHEMA \\"public\\" OWNER TO \\"cruftfree_admin\\";", "REVOKE CREATE ON SCHEMA \\"public\\" FROM PUBLIC;", "REVOKE CONNECT, TEMPORARY ON DATABASE \\"cityservices_facility\\" FROM PUBLIC;", "GRANT CONNECT ON DATABASE \\"cityservices_facility\\" TO \\"cruftfree_admin\\";", "GRANT CONNECT ON DATABASE \\"cityservices_facility\\" TO \\"cityservices_facility_service_facility_db_rw\\";", "GRANT USAGE ON SCHEMA \\"public\\" TO \\"cityservices_facility_service_facility_db_rw\\";", "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA \\"public\\" TO \\"cityservices_facility_service_facility_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \\"cityservices_facility_service_facility_db_rw\\";", "GRANT USAGE ON ALL SEQUENCES IN SCHEMA \\"public\\" TO \\"cityservices_facility_service_facility_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT USAGE ON SEQUENCES TO \\"cityservices_facility_service_facility_db_rw\\";"]}, "cityservices.GeocoderMock.geocoderDb": {"administrator": "cruftfree_admin", "create_login": "CREATE ROLE {login} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "database": "cityservices_geocoder_mock", "external": false, "logins": ["cityservices_geocoder_mock_geocoder_db_rw"], "set_password": "ALTER ROLE {login} WITH LOGIN PASSWORD {password}", "ssl_mode": "verify-full", "ssl_root": "rds-global-bundle.pem", "statements": ["CREATE SCHEMA IF NOT EXISTS \\"public\\" AUTHORIZATION \\"cruftfree_admin\\";", "ALTER SCHEMA \\"public\\" OWNER TO \\"cruftfree_admin\\";", "REVOKE CREATE ON SCHEMA \\"public\\" FROM PUBLIC;", "REVOKE CONNECT, TEMPORARY ON DATABASE \\"cityservices_geocoder_mock\\" FROM PUBLIC;", "GRANT CONNECT ON DATABASE \\"cityservices_geocoder_mock\\" TO \\"cruftfree_admin\\";", "GRANT CONNECT ON DATABASE \\"cityservices_geocoder_mock\\" TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";", "GRANT USAGE ON SCHEMA \\"public\\" TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";", "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA \\"public\\" TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";", "GRANT USAGE ON ALL SEQUENCES IN SCHEMA \\"public\\" TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT USAGE ON SEQUENCES TO \\"cityservices_geocoder_mock_geocoder_db_rw\\";"]}, "cityservices.RequestService.requestDb": {"administrator": "cruftfree_admin", "create_login": "CREATE ROLE {login} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "database": "cityservices_request", "external": false, "logins": ["cityservices_request_service_request_db_rw"], "set_password": "ALTER ROLE {login} WITH LOGIN PASSWORD {password}", "ssl_mode": "verify-full", "ssl_root": "rds-global-bundle.pem", "statements": ["CREATE SCHEMA IF NOT EXISTS \\"public\\" AUTHORIZATION \\"cruftfree_admin\\";", "ALTER SCHEMA \\"public\\" OWNER TO \\"cruftfree_admin\\";", "REVOKE CREATE ON SCHEMA \\"public\\" FROM PUBLIC;", "REVOKE CONNECT, TEMPORARY ON DATABASE \\"cityservices_request\\" FROM PUBLIC;", "GRANT CONNECT ON DATABASE \\"cityservices_request\\" TO \\"cruftfree_admin\\";", "GRANT CONNECT ON DATABASE \\"cityservices_request\\" TO \\"cityservices_request_service_request_db_rw\\";", "GRANT USAGE ON SCHEMA \\"public\\" TO \\"cityservices_request_service_request_db_rw\\";", "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA \\"public\\" TO \\"cityservices_request_service_request_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \\"cityservices_request_service_request_db_rw\\";", "GRANT USAGE ON ALL SEQUENCES IN SCHEMA \\"public\\" TO \\"cityservices_request_service_request_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT USAGE ON SEQUENCES TO \\"cityservices_request_service_request_db_rw\\";"]}, "cityservices.SmsMock.smsDb": {"administrator": "cruftfree_admin", "create_login": "CREATE ROLE {login} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", "database": "cityservices_sms_mock", "external": false, "logins": ["cityservices_sms_mock_sms_db_rw"], "set_password": "ALTER ROLE {login} WITH LOGIN PASSWORD {password}", "ssl_mode": "verify-full", "ssl_root": "rds-global-bundle.pem", "statements": ["CREATE SCHEMA IF NOT EXISTS \\"public\\" AUTHORIZATION \\"cruftfree_admin\\";", "ALTER SCHEMA \\"public\\" OWNER TO \\"cruftfree_admin\\";", "REVOKE CREATE ON SCHEMA \\"public\\" FROM PUBLIC;", "REVOKE CONNECT, TEMPORARY ON DATABASE \\"cityservices_sms_mock\\" FROM PUBLIC;", "GRANT CONNECT ON DATABASE \\"cityservices_sms_mock\\" TO \\"cruftfree_admin\\";", "GRANT CONNECT ON DATABASE \\"cityservices_sms_mock\\" TO \\"cityservices_sms_mock_sms_db_rw\\";", "GRANT USAGE ON SCHEMA \\"public\\" TO \\"cityservices_sms_mock_sms_db_rw\\";", "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA \\"public\\" TO \\"cityservices_sms_mock_sms_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \\"cityservices_sms_mock_sms_db_rw\\";", "GRANT USAGE ON ALL SEQUENCES IN SCHEMA \\"public\\" TO \\"cityservices_sms_mock_sms_db_rw\\";", "ALTER DEFAULT PRIVILEGES FOR ROLE \\"cruftfree_admin\\" IN SCHEMA \\"public\\" GRANT USAGE ON SEQUENCES TO \\"cityservices_sms_mock_sms_db_rw\\";"]}}'
)


def _secret_string(secret_arn: str) -> str:
    """The current ``SecretString`` of *secret_arn*.

    Raises:
        RuntimeError: The secret holds no string value.
    """
    value = (
        boto3.client("secretsmanager")
        .get_secret_value(SecretId=secret_arn)
        .get("SecretString")
    )
    if not isinstance(value, str) or not value:
        raise RuntimeError(
            "A database credential secret holds no string value; the database's access "
            "plan cannot be provisioned without it."
        )
    return value


def _require(properties: Mapping[str, object], key: str) -> str:
    value = properties[key] if key in properties else None
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Custom resource property '{key}' is missing or empty.")
    return value


def _block(properties: Mapping[str, object]) -> dict[str, object]:
    """The table entry of the block the request names.

    Raises:
        RuntimeError: The table names no such block.
    """
    key = _require(properties, "Block")
    if key not in _BLOCKS:
        raise RuntimeError(
            f"No access plan exists for block '{key}'. Known: {sorted(_BLOCKS)}."
        )
    return _BLOCKS[key]


def _strings(entry: Mapping[str, object], key: str) -> list[str]:
    value = entry[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError(f"The access table's '{key}' is not a list of strings.")
    return value


def _login_secrets(
    properties: Mapping[str, object], logins: list[str]
) -> dict[str, str]:
    """The secret ARN of every login of the block, exactly the logins its plan names.

    Raises:
        RuntimeError: The request names a login the plan does not, or misses one.
    """
    secrets = properties["LoginSecretArns"] if "LoginSecretArns" in properties else None
    if not isinstance(secrets, dict) or set(secrets) != set(logins):
        named = sorted(secrets) if isinstance(secrets, dict) else []
        raise RuntimeError(
            f"Custom resource property 'LoginSecretArns' names the logins {named}; the "
            f"block's access plan names {sorted(logins)}."
        )
    return {login: _require(secrets, login) for login in logins}


def _master(
    properties: Mapping[str, object], administrator: str, external: bool
) -> dict[str, str]:
    """The owner credential, refused unless it is the login the grants were rendered for.

    The master secret of a provisioned database is a username/password document; the owner
    password of a block on an external server is the bare password the operator placed, for
    the login the table names.

    Raises:
        RuntimeError: The secret is not a username/password document of *administrator*.
    """
    secret = _secret_string(_require(properties, "AdminSecretArn"))
    if external:
        return {"username": administrator, "password": secret}
    master = json.loads(secret)
    if (
        not isinstance(master, dict)
        or "username" not in master
        or "password" not in master
    ):
        raise RuntimeError(
            "The master credential secret is not a username/password document."
        )
    if master["username"] != administrator:
        raise RuntimeError(
            "The master credential secret names another login than the one the block's "
            "access plan was rendered for."
        )
    return master


def _connection_tls(entry: Mapping[str, object]) -> dict[str, str]:
    """The connection parameters of the TLS the table names: its mode, and its root certificate
    when it names one (the bundle beside this module, by its file name, or the word for the
    system trust store)."""
    tls = {"sslmode": str(entry["ssl_mode"])}
    root = entry["ssl_root"]
    if root is not None:
        tls["sslrootcert"] = _CA_BUNDLE if root == _CA_BUNDLE_FILE else str(root)
    return tls


def _provision(properties: Mapping[str, object]) -> str:
    """Create or re-assert the block's logins and grants; return the physical id."""
    block_key = _require(properties, "Block")
    entry = _block(properties)
    database = str(entry["database"])
    administrator = str(entry["administrator"])
    logins = _strings(entry, "logins")
    secrets = _login_secrets(properties, logins)
    external = bool(entry["external"])
    master = _master(properties, administrator, external)
    create_login = sql.SQL(str(entry["create_login"]))
    set_password = sql.SQL(str(entry["set_password"]))
    with psycopg.connect(
        host=_require(properties, "Host"),
        port=int(_require(properties, "Port")),
        dbname=database,
        user=master["username"],
        password=master["password"],
        connect_timeout=_CONNECT_TIMEOUT_SECONDS,
        autocommit=True,
        **_connection_tls(entry),
    ) as connection:
        with connection.cursor() as cursor:
            for login in logins:
                identifier = sql.Identifier(login)
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (login,))
                if cursor.fetchone() is None:
                    cursor.execute(create_login.format(login=identifier))
                cursor.execute(
                    set_password.format(
                        login=identifier,
                        password=sql.Literal(_secret_string(secrets[login])),
                    )
                )
            for statement in _strings(entry, "statements"):
                cursor.execute(sql.SQL(statement))
    logger.info("rdbms_access_provisioned logins=%d", len(logins))
    return f"rdbms-access:{block_key}"


def _properties(event: Mapping[str, object]) -> dict[str, object]:
    properties = event["ResourceProperties"] if "ResourceProperties" in event else None
    if not isinstance(properties, dict):
        raise RuntimeError("Custom resource event carries no ResourceProperties.")
    return properties


def handler(event: dict[str, object], context: object) -> dict[str, object]:
    """CloudFormation custom-resource event handler (CDK ``Provider`` framework)."""
    del context
    request_type = event["RequestType"] if "RequestType" in event else None
    logger.info("rdbms_access_request type=%s", request_type)
    if request_type == _DELETE:
        return {"PhysicalResourceId": event["PhysicalResourceId"]}
    return {"PhysicalResourceId": _provision(_properties(event))}


def _current_physical_id(event: Mapping[str, object]) -> str:
    """The id CloudFormation already holds for the resource, or the failed-create id."""
    current = event["PhysicalResourceId"] if "PhysicalResourceId" in event else None
    return (
        current
        if isinstance(current, str) and current
        else _FAILED_PHYSICAL_RESOURCE_ID
    )


def _failure_reason(error: Exception) -> str:
    """The reason a failed request reports: this module's own requirement, or the kind
    of error alone -- a driver or SDK message may quote a statement or a host."""
    if isinstance(error, RuntimeError):
        logger.error("rdbms_access FAILED: %s", error)
        return str(error)
    logger.error("rdbms_access FAILED: %s", type(error).__name__)
    return (
        "Provisioning the database access plan failed (%s); see the function's log group."
        % (type(error).__name__)
    )


def cfn_handler(event: Mapping[str, object], context: object) -> None:
    """CloudFormation custom-resource event handler (invoked directly by the stack)."""
    del context
    request_type = event["RequestType"] if "RequestType" in event else None
    logger.info("rdbms_access_request type=%s", request_type)
    if request_type == _DELETE:
        reason = "Delete leaves the database's logins in place with its database."
        _respond(event, _SUCCESS, reason, _current_physical_id(event), {})
        return
    try:
        if request_type not in (_CREATE, _UPDATE):
            raise RuntimeError("Unsupported request type %r." % request_type)
        physical_id = _provision(_properties(event))
    except (
        Exception
    ) as error:  # every fault still answers CloudFormation, which would wait otherwise
        _respond(
            event, _FAILED, _failure_reason(error), _current_physical_id(event), {}
        )
        return
    _respond(
        event, _SUCCESS, "The database access plan is provisioned.", physical_id, {}
    )
