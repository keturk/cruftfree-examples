"""Credential provider. Auto-generated. Do not edit.

Binds the deployment-credential module (``_runtime/deployment_credentials``) to
this service's ``config._bootstrap``: the baked CREDENTIAL_KIND decides which
accessor may be called, and none of them reads configuration from the
environment. AWS clients are signed with the platform-delivered role only.
"""

from __future__ import annotations

from helpdesk_email_mock._runtime.deployment_credentials import DeploymentCredentials
from helpdesk_email_mock.config import _bootstrap

_provider = DeploymentCredentials(_bootstrap)

azure_credential = _provider.azure_credential
azure_credential_sync = _provider.azure_credential_sync
aws_client = _provider.aws_client
aws_assumed_role_client = _provider.aws_assumed_role_client
aws_role_credentials = _provider.aws_role_credentials
bind_aws_role_channel = _provider.bind_aws_role_channel
mounted_file_credential = _provider.mounted_file_credential
select_credential_kind = _provider.select_credential_kind
