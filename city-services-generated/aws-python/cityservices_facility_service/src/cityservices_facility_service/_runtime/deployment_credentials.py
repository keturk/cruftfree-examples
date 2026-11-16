"""The deployment credential of a generated service, built with no environment read.

Emitted verbatim as ``<package>/_runtime/deployment_credentials.py``. The service's
``config/_credentials.py`` binds it to the service's ``config._bootstrap`` module,
whose baked ``CREDENTIAL_KIND`` decides which accessor may be called: every other
accessor refuses, so a credential of the wrong kind is never silently built.
"""

from __future__ import annotations

import logging
from typing import Final, Protocol

logger = logging.getLogger(__name__)

#: The credential kinds a bootstrap bakes (the values of ``CredentialKind``).
AZURE_MANAGED_IDENTITY: Final[str] = "azure-managed-identity"
AWS_INSTANCE_ROLE: Final[str] = "aws-instance-role"
MOUNTED_FILE: Final[str] = "mounted-file"

#: The channels through which the AWS platform hands a process its role credential.
#: A container task or an instance reads its role from the container or instance
#: metadata endpoint; a Lambda execution environment receives its execution role in
#: the runtime's reserved environment variables, which no function configuration can
#: set. Only the Lambda entry point binds the Lambda channel.
AWS_ROLE_CHANNEL_METADATA: Final[str] = "metadata"
AWS_ROLE_CHANNEL_LAMBDA_RUNTIME: Final[str] = "lambda-runtime"
_AWS_ROLE_CHANNELS: Final[frozenset[str]] = frozenset(
    {AWS_ROLE_CHANNEL_METADATA, AWS_ROLE_CHANNEL_LAMBDA_RUNTIME}
)


class CredentialBootstrap(Protocol):
    """What the accessors read from the service's ``config._bootstrap`` module.

    The generated bootstrap module satisfies it. Each value is read on every call,
    never captured at bind time.
    """

    @property
    def CREDENTIAL_KIND(self) -> str:
        """How the service authenticates to its backends."""

    @property
    def REGION(self) -> str | None:
        """The AWS region baked at generation time; unset off AWS."""

    @property
    def CREDENTIAL_FILE_PATH(self) -> str | None:
        """The mounted credential file baked for a LOCAL deployment; unset elsewhere."""


#: The session name an assumed role's credential carries, so CloudTrail attributes
#: each call made with it to a generated service's assumed-role client.
_ASSUMED_ROLE_SESSION_NAME: Final[str] = "cruftfree-service"


class AwsClientFactory(Protocol):
    """What :meth:`DeploymentCredentials.aws_client` reads from its boto3 session."""

    def client(self, service_name: str) -> object:
        """A client of *service_name* in the session's region and credentials."""

    def resource(self, service_name: str, *, region_name: str) -> object:
        """A resource of *service_name* in *region_name*, under the session's credentials."""

    def get_credentials(self) -> object | None:
        """The credential the session signs with, or ``None``."""


class BotocoreSession(Protocol):
    """What the role-channel botocore session is read for."""

    def register_component(self, name: str, component: object) -> None:
        """Install *component* (the credential resolver) under *name*."""

    def get_credentials(self) -> object | None:
        """The credential the registered resolver yields, or ``None``."""

    def create_client(self, service_name: str, **kwargs: object) -> object:
        """A client of *service_name* built with *kwargs*."""


class DeploymentCredentials:
    """Builds the service's deployment credential from baked constants only.

    Args:
        bootstrap: The service's ``config._bootstrap`` module.
    """

    def __init__(self, bootstrap: CredentialBootstrap) -> None:
        self._bootstrap = bootstrap
        self._aws_role_channel = AWS_ROLE_CHANNEL_METADATA
        self._aws_role_session: AwsClientFactory | None = None
        self._aws_assumed_role_sessions: dict[str, AwsClientFactory] = {}

    def bind_aws_role_channel(self, channel: str) -> None:
        """Name the channel the platform delivers this process's AWS role through.

        Every process reads its role from the metadata endpoint unless its entry
        point binds another channel: the Lambda entry point binds the Lambda
        runtime channel before its first invocation. A session built under the
        previous channel is dropped.

        Raises:
            ValueError: *channel* is not a known role channel.
        """
        if channel not in _AWS_ROLE_CHANNELS:
            raise ValueError(
                "Unknown AWS role channel %r. Expected one of %s. "
                "Bind the channel the process's entry point runs on."
                % (channel, sorted(_AWS_ROLE_CHANNELS))
            )
        self._aws_role_channel = channel
        self._aws_role_session = None
        self._aws_assumed_role_sessions = {}
        logger.debug("aws_role_channel_bound channel=%s", channel)

    def select_credential_kind(self) -> str:
        """The baked credential kind, for backends that dispatch on it."""
        return self._bootstrap.CREDENTIAL_KIND

    def _require_kind(self, accessor: str, expected: str) -> None:
        """Refuse *accessor* unless the baked credential kind is *expected*.

        Raises:
            RuntimeError: The baked kind is another one.
        """
        kind = self._bootstrap.CREDENTIAL_KIND
        if kind != expected:
            raise RuntimeError(
                "%s() called but CREDENTIAL_KIND is %r — expected %r. "
                "Verify the deployment profile and regenerate."
                % (accessor, kind, expected)
            )

    def azure_credential(self) -> object:
        """Async managed-identity credential that NEVER consults environment variables.

        Constructs ``ManagedIdentityCredential`` directly, which contacts the Azure
        IMDS endpoint only. No ``EnvironmentCredential`` leg is present, so no
        ``AZURE_*`` variable is consulted.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``azure-managed-identity``.
            ImportError: ``azure-identity`` is not installed.
        """
        self._require_kind("azure_credential", AZURE_MANAGED_IDENTITY)
        try:
            from azure.identity.aio import ManagedIdentityCredential
        except ImportError as exc:
            raise ImportError(
                "azure-identity is not installed. "
                "Add 'azure-identity>=1.18.0' to the service dependencies."
            ) from exc
        logger.debug("credential_provider credential_kind=%s", AZURE_MANAGED_IDENTITY)
        return ManagedIdentityCredential()

    def azure_credential_sync(self) -> object:
        """Synchronous managed-identity credential for synchronous Azure SDK clients.

        The same no-environment managed identity as :meth:`azure_credential`, but the
        *synchronous* ``azure.identity.ManagedIdentityCredential``. Synchronous SDK
        clients (e.g. ``AzureAppConfigurationClient``) call ``credential.get_token``
        directly and read ``.expires_on`` off the result; the async credential would
        hand them an un-awaited coroutine.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``azure-managed-identity``.
            ImportError: ``azure-identity`` is not installed.
        """
        self._require_kind("azure_credential_sync", AZURE_MANAGED_IDENTITY)
        try:
            from azure.identity import ManagedIdentityCredential
        except ImportError as exc:
            raise ImportError(
                "azure-identity is not installed. "
                "Add 'azure-identity>=1.18.0' to the service dependencies."
            ) from exc
        logger.debug(
            "credential_provider credential_kind=%s sync=true", AZURE_MANAGED_IDENTITY
        )
        return ManagedIdentityCredential()

    def aws_client(self, service_name: str) -> object:
        """A boto3 client in the baked region, signed with the platform-delivered role only.

        ``region_name`` is always the baked ``REGION``: ``AWS_REGION`` /
        ``AWS_DEFAULT_REGION`` are never consulted. Credentials never come from
        boto3's default chain, which reads static keys from the environment and
        shared config files before the role: a stray key would replace the
        least-privilege role. See :meth:`_aws_session` for the providers.

        Args:
            service_name: The AWS service (e.g. ``"secretsmanager"``, ``"appconfig"``).

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``aws-instance-role``,
                ``REGION`` is not baked (boto3 would fall back to the environment),
                or the bound role channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        self._require_kind("aws_client", AWS_INSTANCE_ROLE)
        region = self._require_region("aws_client")
        session = self._aws_session(region)
        logger.debug(
            "credential_provider credential_kind=%s channel=%s service=%s region=%s",
            AWS_INSTANCE_ROLE,
            self._aws_role_channel,
            service_name,
            region,
        )
        return session.client(service_name)

    def aws_resource(
        self, service_name: str, *, region_name: str | None = None
    ) -> object:
        """A boto3 resource signed with the platform-delivered role only.

        Args:
            service_name: The AWS service (e.g. ``"dynamodb"``).
            region_name: The region a block declares for its store; the baked ``REGION``
                when it declares none.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``aws-instance-role``,
                ``REGION`` is not baked, or the bound role channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        self._require_kind("aws_resource", AWS_INSTANCE_ROLE)
        region = self._require_region("aws_resource")
        return self._aws_session(region).resource(
            service_name, region_name=region_name or region
        )

    def aws_role_credentials(self) -> object:
        """The platform-delivered role's credential, for a caller presenting it itself.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``aws-instance-role``,
                ``REGION`` is not baked, or the bound role channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        self._require_kind("aws_role_credentials", AWS_INSTANCE_ROLE)
        region = self._require_region("aws_role_credentials")
        credentials = self._aws_session(region).get_credentials()
        if credentials is None:
            raise RuntimeError(
                "aws_role_credentials() found no role credential on the %r channel. Expected "
                "the platform to deliver the service's role. Fix: attach the role to the "
                "task, instance or function this service runs as."
                % (self._aws_role_channel,)
            )
        return credentials

    def aws_assumed_role_client(self, service_name: str, role_arn: str) -> object:
        """A boto3 client in the baked region, signed with *role_arn* assumed by the
        platform-delivered role.

        A grant the deployment confines to a role of its own (the SNS SMS sender
        role, granted ``sns:Publish`` on ``*`` and denied every topic) is used
        through this client only; the service's own role holds just
        ``sts:AssumeRole`` on it. The assumed credential is fetched from STS in the
        baked region when first used and refreshed before it expires, each time
        with the platform-delivered role's current credential.

        Args:
            service_name: The AWS service (e.g. ``"sns"``).
            role_arn: The ARN of the role to assume, delivered by the deployment.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``aws-instance-role``,
                ``REGION`` is not baked, *role_arn* is empty, or the bound role
                channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        self._require_kind("aws_assumed_role_client", AWS_INSTANCE_ROLE)
        region = self._require_region("aws_assumed_role_client")
        if not role_arn:
            raise RuntimeError(
                "aws_assumed_role_client() was given no role ARN. Expected the ARN the "
                "deployment delivered for the role this client sends as. Fix: verify the "
                "deployment created the role and wired its ARN as an application setting."
            )
        session = self._aws_assumed_role_sessions.get(role_arn)
        if session is None:
            session = self._assumed_role_session(region, role_arn)
            self._aws_assumed_role_sessions[role_arn] = session
        logger.debug(
            "credential_provider credential_kind=%s channel=%s service=%s region=%s "
            "assumed_role=%s",
            AWS_INSTANCE_ROLE,
            self._aws_role_channel,
            service_name,
            region,
            role_arn,
        )
        return session.client(service_name)

    def _require_region(self, accessor: str) -> str:
        """The baked ``REGION``.

        Raises:
            RuntimeError: ``REGION`` is not baked (boto3 would fall back to the
                environment).
        """
        region = self._bootstrap.REGION
        if not region:
            raise RuntimeError(
                "%s() requires a baked REGION constant but REGION is None. "
                "The generator must bake the AWS region at generation time so boto3 "
                "never falls back to AWS_REGION env. Regenerate with a resolved region."
                % (accessor,)
            )
        return region

    def _aws_session(self, region: str) -> AwsClientFactory:
        """The process's boto3 session, whose only credential source is the bound role channel.

        Built once and reused: the role credential refreshes itself before it expires.

        Raises:
            RuntimeError: The bound channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        if self._aws_role_session is not None:
            return self._aws_role_session
        import boto3

        session: AwsClientFactory = boto3.session.Session(
            botocore_session=self._aws_role_core_session(), region_name=region
        )
        self._aws_role_session = session
        return session

    def _aws_role_core_session(self) -> BotocoreSession:
        """A botocore session whose only credential source is the bound role channel.

        The metadata channel resolves through the container credentials endpoint
        (an ECS or App Runner task role) and then the instance metadata endpoint
        (an EC2 instance role); the Lambda runtime channel reads the execution
        role from the runtime's reserved environment variables.

        Raises:
            RuntimeError: The bound channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        try:
            import botocore.session
            from botocore.credentials import (
                ContainerProvider,
                CredentialResolver,
                EnvProvider,
                InstanceMetadataFetcher,
                InstanceMetadataProvider,
            )
        except ImportError as exc:
            raise ImportError(
                "boto3 is not installed. Add 'boto3>=1.41.0' to the service dependencies."
            ) from exc
        if self._aws_role_channel == AWS_ROLE_CHANNEL_LAMBDA_RUNTIME:
            providers: list[object] = [EnvProvider()]
        else:
            providers = [
                ContainerProvider(),
                InstanceMetadataProvider(iam_role_fetcher=InstanceMetadataFetcher()),
            ]
        core: BotocoreSession = botocore.session.Session()
        core.register_component(
            "credential_provider", CredentialResolver(providers=providers)
        )
        if core.get_credentials() is None:
            raise RuntimeError(
                "aws_client() found no role credential on the %r channel. Expected the "
                "platform to deliver the service's role (an ECS or App Runner task role, "
                "an EC2 instance role, or a Lambda execution role); static keys from the "
                "environment or shared config files are never used. Fix: attach the "
                "role to the task, instance or function this service runs as."
                % (self._aws_role_channel,)
            )
        return core

    def _assumed_role_session(self, region: str, role_arn: str) -> AwsClientFactory:
        """A boto3 session signed with *role_arn*, assumed through STS in *region* by the
        role-channel credential.

        Raises:
            RuntimeError: The bound channel yields no credential.
            ImportError: ``boto3`` is not installed.
        """
        import functools

        import boto3
        import botocore.session
        from botocore.credentials import (
            AssumeRoleCredentialFetcher,
            CredentialProvider,
            CredentialResolver,
            DeferredRefreshableCredentials,
        )

        source = self._aws_role_core_session()
        fetcher = AssumeRoleCredentialFetcher(
            client_creator=functools.partial(source.create_client, region_name=region),
            source_credentials=source.get_credentials(),
            role_arn=role_arn,
            extra_args={"RoleSessionName": _ASSUMED_ROLE_SESSION_NAME},
        )

        class _AssumedRoleProvider(CredentialProvider):
            METHOD = "assume-role"

            def load(self) -> object:
                return DeferredRefreshableCredentials(
                    method=self.METHOD, refresh_using=fetcher.fetch_credentials
                )

        core: BotocoreSession = botocore.session.Session()
        core.register_component(
            "credential_provider",
            CredentialResolver(providers=[_AssumedRoleProvider()]),
        )
        session: AwsClientFactory = boto3.session.Session(
            botocore_session=core, region_name=region
        )
        return session

    def mounted_file_credential(self) -> str:
        """The path of the mounted credential file (LOCAL / docker).

        The path is the baked ``CREDENTIAL_FILE_PATH``, never an environment variable.

        Raises:
            RuntimeError: ``CREDENTIAL_KIND`` is not ``mounted-file``, or
                ``CREDENTIAL_FILE_PATH`` is not baked.
        """
        self._require_kind("mounted_file_credential", MOUNTED_FILE)
        path = self._bootstrap.CREDENTIAL_FILE_PATH
        if not path:
            raise RuntimeError(
                "CREDENTIAL_FILE_PATH is not baked; cannot resolve mounted-file credential. "
                "The generator must bake the credential file path for LOCAL deployments. "
                "Regenerate with a resolved CREDENTIAL_FILE_PATH."
            )
        logger.debug(
            "credential_provider credential_kind=%s path=%s", MOUNTED_FILE, path
        )
        return path
