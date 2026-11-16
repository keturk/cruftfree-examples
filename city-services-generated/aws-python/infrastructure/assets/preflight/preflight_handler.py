"""Custom resource: the deployment preflight of the application's secrets and config keys.

CloudFormation invokes this function from two places. The preflight stack, created or
updated before any stack that reads a secret, sends one item per secret the
application's runtime requirements name (``SecretItems``). Each item's action decides
what happens:

* a CruftFree-owned secret is generated once when missing, tagged CruftFree-generated, and
  never overwritten while usable; an unusable one fails the deploy unless the item
  requests a repair;
* the CruftFree-owned keypair is generated only when both halves are missing,
  preserved when both are usable, and fails the deploy when only one is;
* an operator-owned secret is checked and never written: every required one without a
  usable value is collected, and the deploy fails once, naming them all;
* an optional operator-owned secret is reported and never fails the deploy.

A service stack that declares the AppConfig store sends one item per config key of the
profiles it declares (``ConfigItems``), after its store's deployments and before its
compute starts. Each item names its application, environment and profile by id:

* a key with a declared default is seeded from it when it has no value, and a present
  value is never overwritten; a feature-flag profile keeps its ``flags``/``values``
  shape; every seed of one profile lands in one new version, deployed all at once;
* a key with no default is checked: every one without a value is collected, and the
  deploy fails once, naming each profile and key.

A request carries exactly one of the two item lists. A Delete request touches nothing:
the secrets and the config values outlive the stack. Every outcome is sent to the
pre-signed response URL CloudFormation supplies, over HTTPS only; a failure is sent as
FAILED with a reason naming handles, rendered secret names, profiles and keys, never a
value. No secret or config value is ever logged.
"""

from __future__ import annotations

import json
import logging
import secrets
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
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


_CREATE: Final[str] = "Create"
_UPDATE: Final[str] = "Update"
_DELETE: Final[str] = "Delete"
_PHYSICAL_RESOURCE_ID: Final[str] = "cruftfree-preflight"

_SERVICE_TOKEN: Final[str] = "ServiceToken"
_SERVICE_TIMEOUT: Final[str] = "ServiceTimeout"
_RUN_ID: Final[str] = "RunId"
_SECRET_ITEMS: Final[str] = "SecretItems"
_CONFIG_ITEMS: Final[str] = "ConfigItems"
_PROPERTIES: Final[frozenset[str]] = frozenset(
    {_SERVICE_TOKEN, _SERVICE_TIMEOUT, _RUN_ID, _SECRET_ITEMS, _CONFIG_ITEMS}
)

_ACTION: Final[str] = "action_fn"
_ITEM_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "generate_owned_secret_if_missing": ("handle", "secret_name", "rotate_repair"),
    "generate_owned_cipher_key_if_missing": ("handle", "secret_name"),
    "generate_owned_keypair_if_missing": (
        "public_handle",
        "public_secret_name",
        "private_handle",
        "private_secret_name",
    ),
    "check_operator_secret": ("handle", "secret_name", "owning_integration", "effect"),
    "report_optional_operator_secret": (
        "handle",
        "secret_name",
        "owning_integration",
        "effect",
    ),
    "require_platform_written_secret": ("handle", "secret_name"),
}
_CONFIG_ITEM_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "seed_config_default": (
        "application",
        "environment",
        "profile",
        "key",
        "content_shape",
        "default_value",
    ),
    "check_config_key": ("application", "environment", "profile", "key"),
}
#: Each item list -> the actions its items may carry and the fields each one's item carries.
_ITEM_CONTRACTS: Final[Mapping[str, Mapping[str, tuple[str, ...]]]] = {
    _SECRET_ITEMS: _ITEM_FIELDS,
    _CONFIG_ITEMS: _CONFIG_ITEM_FIELDS,
}
_ROTATE_REPAIR: Final[str] = "rotate_repair"
_HANDLE: Final[str] = "handle"
_SECRET_NAME: Final[str] = "secret_name"
_OWNING_INTEGRATION: Final[str] = "owning_integration"
_EFFECT: Final[str] = "effect"
_PUBLIC_HANDLE: Final[str] = "public_handle"
_PUBLIC_SECRET_NAME: Final[str] = "public_secret_name"
_PRIVATE_HANDLE: Final[str] = "private_handle"
_PRIVATE_SECRET_NAME: Final[str] = "private_secret_name"
_TRUE: Final[str] = "true"
_FALSE: Final[str] = "false"

_APPLICATION: Final[str] = "application"
_ENVIRONMENT: Final[str] = "environment"
_PROFILE: Final[str] = "profile"
_KEY: Final[str] = "key"
_CONTENT_SHAPE: Final[str] = "content_shape"
_DEFAULT_VALUE: Final[str] = "default_value"
_SHAPE_FREEFORM: Final[str] = "freeform"
_SHAPE_FEATURE_FLAG: Final[str] = "feature-flag"
_CONTENT_SHAPES: Final[frozenset[str]] = frozenset(
    {_SHAPE_FREEFORM, _SHAPE_FEATURE_FLAG}
)
_FREEFORM_CONTENT_TYPE: Final[str] = "application/json"
_FEATURE_FLAG_CONTENT_TYPE: Final[str] = "application/x-amzn-appconfig-feature-flags"
_FEATURE_FLAG_SCHEMA_VERSION: Final[str] = "1"
_SEED_DEPLOYMENT_STRATEGY: Final[str] = "AppConfig.AllAtOnce"
_FLAGS: Final[str] = "flags"
_VALUES: Final[str] = "values"
_VERSION: Final[str] = "version"
_ENABLED: Final[str] = "enabled"
_NAME: Final[str] = "name"

_GENERATED_TAG: Final[Mapping[str, str]] = {
    "Key": "cruftfree:provisioned-by",
    "Value": "cruftfree",
}
_GENERATED_SECRET_BYTES: Final[int] = 48
_KEYPAIR_BITS: Final[int] = 3072
_CIPHER_KEY_BYTES: Final[int] = 32

_NOT_FOUND: Final[str] = "ResourceNotFoundException"
_CURRENT_STAGE: Final[str] = "AWSCURRENT"
_MISSING: Final[str] = "missing"
_PENDING_DELETION: Final[str] = "pending-deletion"
_EMPTY: Final[str] = "empty"
_DISABLED: Final[str] = "disabled"
_USABLE: Final[str] = "usable"

Item = Mapping[str, str]
#: One configuration profile a config item targets: (application, environment, profile).
ProfileTarget = tuple[str, str, str]


class PreflightFailure(Exception):
    """A requirement is unmet; the message names handles, secret names, profiles and
    keys, never a value."""


def _secret_state(client: object, secret_name: str) -> str:
    """Classify a Secrets Manager secret from its metadata alone: missing,
    pending-deletion, empty (no current version) or usable. Reads no value, so the
    function holds no generated or platform-written credential."""
    try:
        described = client.describe_secret(SecretId=secret_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == _NOT_FOUND:
            return _MISSING
        raise
    if described.get("DeletedDate") is not None:
        return _PENDING_DELETION
    version_stages = described.get("VersionIdsToStages") or {}
    if not any(_CURRENT_STAGE in stages for stages in version_stages.values()):
        return _EMPTY
    return _USABLE


def _operator_secret_state(client: object, secret_name: str) -> str:
    """Classify an operator secret: the one kind whose value is read, since an operator
    can store an empty or binary value its metadata does not show, or one the function
    cannot read (disabled). Never returns or logs the value."""
    state = _secret_state(client, secret_name)
    if state != _USABLE:
        return state
    try:
        value = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == _NOT_FOUND:
            return _MISSING
        return _DISABLED
    secret_string = value.get("SecretString")
    if secret_string is None or len(secret_string) == 0:
        return _EMPTY
    return _USABLE


def _create_generated(client: object, secret_name: str, value: str) -> None:
    client.create_secret(
        Name=secret_name, SecretString=value, Tags=[dict(_GENERATED_TAG)]
    )


def _generate_owned_secret_if_missing(client: object, item: Item) -> None:
    """Generate a CruftFree-owned secret once when missing; never overwrite a usable one.

    A disabled, pending-deletion or empty secret fails the deploy unless the item
    requests a repair.
    """
    handle, secret_name = item[_HANDLE], item[_SECRET_NAME]
    state = _secret_state(client, secret_name)
    if state == _USABLE:
        logger.info(
            "cruftfree-owned secret %r (rendered %r) already usable -- preserving",
            handle,
            secret_name,
        )
        return
    if state == _MISSING:
        _create_generated(
            client, secret_name, secrets.token_urlsafe(_GENERATED_SECRET_BYTES)
        )
        logger.info(
            "cruftfree-owned secret %r (rendered %r) generated once and tagged",
            handle,
            secret_name,
        )
        return
    if item[_ROTATE_REPAIR] == _TRUE:
        client.put_secret_value(
            SecretId=secret_name,
            SecretString=secrets.token_urlsafe(_GENERATED_SECRET_BYTES),
        )
        logger.info(
            "cruftfree-owned secret %r (rendered %r) repaired (state was %s)",
            handle,
            secret_name,
            state,
        )
        return
    raise PreflightFailure(
        "CruftFree-owned secret %r (rendered %r) is %s and its item requests no repair. "
        "Restore the secret, or delete it so the preflight generates it again, then "
        "re-deploy." % (handle, secret_name, state)
    )


def _generate_owned_cipher_key_if_missing(client: object, item: Item) -> None:
    """Generate a CruftFree-owned field cipher key once when missing; never replace one.

    The key is 32 random bytes as unpadded base64url, the format the services' cipher
    reads. Replacing a key makes every value stored under it unreadable, so a secret that
    exists in any state but usable fails the deploy and is never repaired here.
    """
    handle, secret_name = item[_HANDLE], item[_SECRET_NAME]
    state = _secret_state(client, secret_name)
    if state == _USABLE:
        logger.info(
            "cruftfree-owned cipher key %r (rendered %r) already usable -- preserving",
            handle,
            secret_name,
        )
        return
    if state == _MISSING:
        _create_generated(client, secret_name, secrets.token_urlsafe(_CIPHER_KEY_BYTES))
        logger.info(
            "cruftfree-owned cipher key %r (rendered %r) generated once and tagged",
            handle,
            secret_name,
        )
        return
    raise PreflightFailure(
        "CruftFree-owned cipher key %r (rendered %r) is %s. Values stored under it are "
        "unreadable without it, so the preflight never replaces it. Restore the secret "
        "from its recovery window or a backup, then re-deploy."
        % (handle, secret_name, state)
    )


def _generate_rsa_pem() -> tuple[str, str]:
    """Return (private_pem, public_pem) for a fresh RSA keypair."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=_KEYPAIR_BITS)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


def _generate_owned_keypair_if_missing(client: object, item: Item) -> None:
    """Generate the CruftFree-owned RSA keypair only when both halves are missing.

    Both halves usable are preserved (an operator-supplied key is never overwritten);
    one half without the other fails the deploy, since a mismatched pair cannot verify
    what it signs. Key material is never logged.
    """
    public_handle, public_name = item[_PUBLIC_HANDLE], item[_PUBLIC_SECRET_NAME]
    private_handle, private_name = item[_PRIVATE_HANDLE], item[_PRIVATE_SECRET_NAME]
    public_state = _secret_state(client, public_name)
    private_state = _secret_state(client, private_name)
    if public_state == _USABLE and private_state == _USABLE:
        logger.info(
            "cruftfree-owned keypair %r/%r already usable -- preserving",
            public_handle,
            private_handle,
        )
        return
    if public_state == _MISSING and private_state == _MISSING:
        private_pem, public_pem = _generate_rsa_pem()
        _create_generated(client, private_name, private_pem)
        _create_generated(client, public_name, public_pem)
        logger.info(
            "cruftfree-owned keypair %r/%r generated once and tagged",
            public_handle,
            private_handle,
        )
        return
    raise PreflightFailure(
        "CruftFree-owned keypair %r (rendered %r) / %r (rendered %r) is inconsistent "
        "(public %s, private %s). A keypair is one unit: delete both halves so the "
        "preflight generates a new pair, or restore the matching counterpart, then "
        "re-deploy."
        % (
            public_handle,
            public_name,
            private_handle,
            private_name,
            public_state,
            private_state,
        )
    )


def _check_operator_secret(client: object, item: Item, unset: list[Item]) -> None:
    """Record an operator secret with no usable value for the end-of-run failure; never
    write one."""
    handle, secret_name = item[_HANDLE], item[_SECRET_NAME]
    state = _operator_secret_state(client, secret_name)
    if state == _USABLE:
        logger.info(
            "operator secret %r (rendered %r) present -- real value kept",
            handle,
            secret_name,
        )
        return
    unset.append({**item, "state": state})
    logger.error(
        "operator secret %r (rendered %r) is %s -- no usable value is set",
        handle,
        secret_name,
        state,
    )


def _report_optional_operator_secret(client: object, item: Item) -> None:
    """Report an operator secret declared ``required = false``; never fail, never write."""
    handle, secret_name = item[_HANDLE], item[_SECRET_NAME]
    state = _operator_secret_state(client, secret_name)
    if state == _USABLE:
        logger.info(
            "optional operator secret %r (rendered %r) present -- real value kept",
            handle,
            secret_name,
        )
        return
    logger.warning(
        "optional operator secret %r (rendered %r, integration %s) is %s -- declared "
        "'required = false', so the deploy continues; effect: %s; to supply it: aws "
        "secretsmanager put-secret-value --secret-id %s --secret-string <REAL_VALUE>",
        handle,
        secret_name,
        item[_OWNING_INTEGRATION],
        state,
        item[_EFFECT],
        secret_name,
    )


def _require_platform_written_secret(client: object, item: Item) -> None:
    """Verify a secret the deployment's own template writes; never write one.

    The template writes it from the resource it creates, so an absent value means that
    step did not run or did not write it. A generated or operator-set stand-in would
    replace the resource's real value, so the deploy fails instead.
    """
    handle, secret_name = item[_HANDLE], item[_SECRET_NAME]
    state = _secret_state(client, secret_name)
    if state == _USABLE:
        logger.info(
            "platform-written secret %r (rendered %r) present", handle, secret_name
        )
        return
    raise PreflightFailure(
        "Platform-written secret %r (rendered %r) is %s. This deployment's template writes "
        "it from the resource it provisions; CruftFree never generates a value for it and an "
        "operator must not set one. Check the stack resource that writes %r, then "
        "re-deploy." % (handle, secret_name, state, secret_name)
    )


#: The actions that never fail on another item's account.
_ACTIONS: Final[Mapping[str, Callable[[object, Item], None]]] = {
    "generate_owned_secret_if_missing": _generate_owned_secret_if_missing,
    "generate_owned_keypair_if_missing": _generate_owned_keypair_if_missing,
    "generate_owned_cipher_key_if_missing": _generate_owned_cipher_key_if_missing,
    "report_optional_operator_secret": _report_optional_operator_secret,
    "require_platform_written_secret": _require_platform_written_secret,
}
#: The actions whose gaps are collected and fail the deploy together.
_AGGREGATED_ACTIONS: Final[Mapping[str, Callable[[object, Item, list[Item]], None]]] = {
    "check_operator_secret": _check_operator_secret,
}


def _fail_if_operator_secrets_unset(unset: Sequence[Item]) -> None:
    """Fail the deploy naming every operator secret without a usable value."""
    if not unset:
        return
    for entry in unset:
        logger.error(
            "operator-owned secret unset: %s (rendered %s, integration %s, state %s); "
            "effect: %s; fix: aws secretsmanager put-secret-value --secret-id %s "
            "--secret-string <REAL_VALUE>",
            entry[_HANDLE],
            entry[_SECRET_NAME],
            entry[_OWNING_INTEGRATION],
            entry["state"],
            entry[_EFFECT],
            entry[_SECRET_NAME],
        )
    listed = ", ".join(
        "%s (rendered %s, %s)" % (e[_HANDLE], e[_SECRET_NAME], e["state"])
        for e in unset
    )
    raise PreflightFailure(
        "%d operator-owned secret(s) have no usable value: %s. CruftFree never writes an "
        "operator-owned secret: set each real value with 'aws secretsmanager "
        "put-secret-value --secret-id <rendered name> --secret-string <REAL_VALUE>', "
        "then re-deploy." % (len(unset), listed)
    )


def _run_secret_items(items: Sequence[Item]) -> None:
    """Run every secret item; operator gaps are collected and fail together at the end."""
    client = boto3.client("secretsmanager")
    unset: list[Item] = []
    for item in items:
        action = item[_ACTION]
        if action in _AGGREGATED_ACTIONS:
            _AGGREGATED_ACTIONS[action](client, item, unset)
        else:
            _ACTIONS[action](client, item)
    _fail_if_operator_secrets_unset(unset)


def _target(item: Item) -> ProfileTarget:
    return item[_APPLICATION], item[_ENVIRONMENT], item[_PROFILE]


def _read_payload(data_client: object, target: ProfileTarget) -> dict[str, object]:
    """The profile's deployed content as a JSON object; empty when nothing is deployed.

    Content that is not a JSON object fails the deploy: writing a seed over it would
    replace what an operator deployed.
    """
    application, environment, profile = target
    session = data_client.start_configuration_session(
        ApplicationIdentifier=application,
        EnvironmentIdentifier=environment,
        ConfigurationProfileIdentifier=profile,
    )
    response = data_client.get_latest_configuration(
        ConfigurationToken=session["InitialConfigurationToken"]
    )
    content = response["Configuration"].read()
    if not content:
        return {}
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    if not isinstance(payload, dict):
        raise PreflightFailure(
            "Configuration profile %r of application %r holds content that is not a JSON "
            "object, so its keys cannot be read. Deploy a JSON object to the profile, "
            "then re-deploy." % (profile, application)
        )
    return payload


def _is_feature_flag_payload(payload: Mapping[str, object]) -> bool:
    return _VERSION in payload and isinstance(payload.get(_FLAGS), dict)


def _feature_flag_values(payload: Mapping[str, object]) -> dict[str, object]:
    """The flag name -> enabled state a feature-flag payload carries."""
    raw_values = payload.get(_VALUES)
    values_by_flag = raw_values if isinstance(raw_values, dict) else {}
    decoded: dict[str, object] = {}
    for flag_name, flag_body in payload[_FLAGS].items():
        if not isinstance(flag_body, dict):
            continue
        value_body = values_by_flag.get(flag_name)
        if isinstance(value_body, dict) and _ENABLED in value_body:
            enabled = value_body[_ENABLED]
        else:
            enabled = flag_body.get(_ENABLED)
        if isinstance(enabled, bool):
            decoded[str(flag_name)] = enabled
    return decoded


def _key_values(payload: Mapping[str, object]) -> dict[str, object]:
    """The key -> value a profile's payload carries, of either content shape."""
    if _is_feature_flag_payload(payload):
        return _feature_flag_values(payload)
    return {str(key): value for key, value in payload.items()}


def _has_value(values: Mapping[str, object], key: str) -> bool:
    """A missing key and an empty value both read as "no value"."""
    return key in values and values[key] is not None and values[key] != ""


def _seeded_payload(
    payload: dict[str, object], seeds: Sequence[Item]
) -> tuple[dict[str, object], str]:
    """``payload`` with every seed's default set, and the content type to write it as."""
    if seeds[0][_CONTENT_SHAPE] != _SHAPE_FEATURE_FLAG:
        return {
            **payload,
            **{seed[_KEY]: json.loads(seed[_DEFAULT_VALUE]) for seed in seeds},
        }, _FREEFORM_CONTENT_TYPE
    if not (
        isinstance(payload.get(_FLAGS), dict) and isinstance(payload.get(_VALUES), dict)
    ):
        payload = {_VERSION: _FEATURE_FLAG_SCHEMA_VERSION, _FLAGS: {}, _VALUES: {}}
    for seed in seeds:
        payload[_FLAGS][seed[_KEY]] = {_NAME: seed[_KEY]}
        payload[_VALUES][seed[_KEY]] = {_ENABLED: json.loads(seed[_DEFAULT_VALUE])}
    return payload, _FEATURE_FLAG_CONTENT_TYPE


def _seed_profile(
    appconfig: object, data_client: object, target: ProfileTarget, items: Sequence[Item]
) -> None:
    """Seed every key of one profile that has no value from its default, in one new
    version deployed all at once; never overwrite a present value."""
    payload = _read_payload(data_client, target)
    values = _key_values(payload)
    seeds = [item for item in items if not _has_value(values, item[_KEY])]
    for item in items:
        if item not in seeds:
            logger.info(
                "config key %r/%r already present -- preserving existing value",
                item[_PROFILE],
                item[_KEY],
            )
    if not seeds:
        return
    application, environment, profile = target
    content, content_type = _seeded_payload(payload, seeds)
    version = appconfig.create_hosted_configuration_version(
        ApplicationId=application,
        ConfigurationProfileId=profile,
        ContentType=content_type,
        Content=json.dumps(content, sort_keys=True).encode("utf-8"),
    )
    appconfig.start_deployment(
        ApplicationId=application,
        EnvironmentId=environment,
        ConfigurationProfileId=profile,
        ConfigurationVersion=str(version["VersionNumber"]),
        DeploymentStrategyId=_SEED_DEPLOYMENT_STRATEGY,
    )
    for seed in seeds:
        logger.info(
            "config key %r/%r seeded from declared default", profile, seed[_KEY]
        )


def _by_target(items: Sequence[Item]) -> dict[ProfileTarget, list[Item]]:
    grouped: dict[ProfileTarget, list[Item]] = {}
    for item in items:
        grouped.setdefault(_target(item), []).append(item)
    return grouped


def _seed_config_defaults(
    appconfig: object, data_client: object, items: Sequence[Item]
) -> None:
    """Seed the keys of every profile the seed items name."""
    for target, profile_items in _by_target(items).items():
        shapes = {item[_CONTENT_SHAPE] for item in profile_items}
        if len(shapes) != 1:
            raise PreflightFailure(
                "Seed items of profile %r carry content shapes %s; one profile has one "
                "shape. Regenerate the stack." % (target[2], sorted(shapes))
            )
        _seed_profile(appconfig, data_client, target, profile_items)


def _check_config_keys(
    appconfig: object, data_client: object, items: Sequence[Item]
) -> None:
    """Fail the deploy naming every config key with no value and no declared default."""
    del appconfig
    missing: list[Item] = []
    for target, profile_items in _by_target(items).items():
        values = _key_values(_read_payload(data_client, target))
        for item in profile_items:
            if _has_value(values, item[_KEY]):
                logger.info("config key %r/%r present", item[_PROFILE], item[_KEY])
                continue
            missing.append(item)
            logger.error(
                "required config key %r/%r has no value", item[_PROFILE], item[_KEY]
            )
    if missing:
        listed = ", ".join("%s/%s" % (item[_PROFILE], item[_KEY]) for item in missing)
        raise PreflightFailure(
            "%d required config key(s) have no value and no declared default (profile/key): "
            "%s. Set each key in the configuration profile, then re-deploy."
            % (len(missing), listed)
        )


#: The config actions, in the order they run: seeds first, then the checks, whose gaps
#: fail together.
_CONFIG_ACTIONS: Final[
    Mapping[str, Callable[[object, object, Sequence[Item]], None]]
] = {
    "seed_config_default": _seed_config_defaults,
    "check_config_key": _check_config_keys,
}


def _run_config_items(items: Sequence[Item]) -> None:
    """Run every config item, one action at a time."""
    appconfig, data_client = boto3.client("appconfig"), boto3.client("appconfigdata")
    for action, run in _CONFIG_ACTIONS.items():
        selected = [item for item in items if item[_ACTION] == action]
        if selected:
            run(appconfig, data_client, selected)


#: Each item list -> the function running its items.
_RUNNERS: Final[Mapping[str, Callable[[Sequence[Item]], None]]] = {
    _SECRET_ITEMS: _run_secret_items,
    _CONFIG_ITEMS: _run_config_items,
}


def _require_default_value(item: Item, index: int) -> None:
    """A seed item's content shape is known and its default is JSON text of that shape."""
    if item[_CONTENT_SHAPE] not in _CONTENT_SHAPES:
        raise PreflightFailure(
            "Config item %d sets %s to %r; expected one of %s."
            % (index, _CONTENT_SHAPE, item[_CONTENT_SHAPE], sorted(_CONTENT_SHAPES))
        )
    try:
        default = json.loads(item[_DEFAULT_VALUE])
    except json.JSONDecodeError:
        raise PreflightFailure(
            "Config item %d (profile %r, key %r) carries a default that is not JSON text."
            % (index, item[_PROFILE], item[_KEY])
        ) from None
    if item[_CONTENT_SHAPE] == _SHAPE_FEATURE_FLAG and not isinstance(default, bool):
        raise PreflightFailure(
            "Config item %d (profile %r, key %r) seeds a feature flag with a non-Boolean "
            "default; a feature-flag profile seeds only true or false."
            % (index, item[_PROFILE], item[_KEY])
        )


def _item(raw: object, index: int, list_name: str) -> Item:
    """One validated item: its action is one its list carries, it carries exactly that
    action's fields, each a non-empty string."""
    contract = _ITEM_CONTRACTS[list_name]
    if not isinstance(raw, dict):
        raise PreflightFailure("%s item %d is not an object." % (list_name, index))
    action = raw[_ACTION] if _ACTION in raw else None
    if action not in contract:
        raise PreflightFailure(
            "%s item %d has action %r; expected one of %s."
            % (list_name, index, action, sorted(contract))
        )
    expected = {_ACTION, *contract[action]}
    if set(raw) != expected:
        raise PreflightFailure(
            "%s item %d (action %s) carries fields %s; expected exactly %s."
            % (list_name, index, action, sorted(raw), sorted(expected))
        )
    blank = sorted(
        key for key, value in raw.items() if not isinstance(value, str) or not value
    )
    if blank:
        raise PreflightFailure(
            "%s item %d (action %s) has empty fields %s."
            % (list_name, index, action, blank)
        )
    if _ROTATE_REPAIR in raw and raw[_ROTATE_REPAIR] not in (_TRUE, _FALSE):
        raise PreflightFailure(
            "%s item %d sets %s to %r; expected %r or %r."
            % (list_name, index, _ROTATE_REPAIR, raw[_ROTATE_REPAIR], _TRUE, _FALSE)
        )
    if _DEFAULT_VALUE in raw:
        _require_default_value(raw, index)
    return raw


def _items(event: Mapping[str, object]) -> tuple[str, list[Item]]:
    """The request's item list name and items, after refusing any property the stacks do
    not declare and a request carrying both item lists or neither."""
    properties = event["ResourceProperties"] if "ResourceProperties" in event else None
    if not isinstance(properties, dict):
        raise PreflightFailure("The request carries no ResourceProperties object.")
    unknown = sorted(set(properties) - _PROPERTIES)
    if unknown:
        raise PreflightFailure(
            "The request carries undeclared properties %s." % unknown
        )
    run_id = properties[_RUN_ID] if _RUN_ID in properties else None
    if not isinstance(run_id, str) or not run_id:
        raise PreflightFailure("The request carries no %s." % _RUN_ID)
    lists = sorted(name for name in _ITEM_CONTRACTS if name in properties)
    if len(lists) != 1:
        raise PreflightFailure(
            "The request carries item lists %s; expected exactly one of %s."
            % (lists, sorted(_ITEM_CONTRACTS))
        )
    list_name = lists[0]
    raw_items = properties[list_name]
    if not isinstance(raw_items, list) or not raw_items:
        raise PreflightFailure("The request's %s is not a non-empty list." % list_name)
    return list_name, [
        _item(raw, index, list_name) for index, raw in enumerate(raw_items)
    ]


def _outcome(event: Mapping[str, object]) -> tuple[str, str]:
    """The (status, reason) to report for *event*; never raises."""
    request_type = event["RequestType"] if "RequestType" in event else None
    if request_type == _DELETE:
        return (
            _SUCCESS,
            "Delete touches nothing: the secrets and config values outlive the stack.",
        )
    try:
        if request_type not in (_CREATE, _UPDATE):
            raise PreflightFailure("Unsupported request type %r." % request_type)
        list_name, items = _items(event)
        _RUNNERS[list_name](items)
    except PreflightFailure as failure:
        logger.error("preflight FAILED: %s", failure)
        return _FAILED, str(failure)
    except ClientError as error:
        code = error.response["Error"]["Code"]
        logger.error(
            "preflight FAILED: AWS refused %s (%s)", error.operation_name, code
        )
        return (
            _FAILED,
            "AWS refused the preflight call %s (%s); see the function's log group."
            % (
                error.operation_name,
                code,
            ),
        )
    except (
        Exception
    ):  # every fault still answers CloudFormation, which would wait otherwise
        logger.exception("preflight FAILED: unexpected error")
        return (
            _FAILED,
            "The preflight failed unexpectedly; see the function's log group.",
        )
    logger.info("preflight PASSED -- every %s requirement is satisfied", list_name)
    return _SUCCESS, "Every %s requirement is satisfied." % list_name


def handler(event: Mapping[str, object], context: object) -> None:
    """CloudFormation custom-resource event handler (invoked directly by the stack)."""
    del context
    logger.info(
        "preflight_request type=%s",
        event["RequestType"] if "RequestType" in event else None,
    )
    status, reason = _outcome(event)
    _respond(event, status, reason, _PHYSICAL_RESOURCE_ID, {})
