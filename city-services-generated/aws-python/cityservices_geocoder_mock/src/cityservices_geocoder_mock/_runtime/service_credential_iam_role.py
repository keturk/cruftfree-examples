"""AWS role credentials as a generated service's machine identity.

Emitted verbatim as ``<package>/_runtime/service_credential_iam_role.py`` beside
``service_credential_core`` for a service whose platform's machine-identity
strategy is ``iam-role``. The credential is the session token of the task or
instance role's temporary credentials, issued by the platform and read through the
role channel alone, so a static key in the environment never stands in for it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol


class FrozenRoleCredentials(Protocol):
    """What the role credential's frozen form is read for."""

    @property
    def token(self) -> str | None:
        """The session token; ``None`` on a credential that is not a role session."""


class RoleCredentials(Protocol):
    """The platform-delivered role's credential."""

    def get_frozen_credentials(self) -> FrozenRoleCredentials:
        """The credential's current values."""


class RoleSessionCredential:
    """Mints the role session token one outbound call presents.

    Args:
        role_credentials: Reads the platform-delivered role's credential, failing closed
            when the platform delivers none (``DeploymentCredentials.aws_role_credentials``).
    """

    def __init__(self, *, role_credentials: Callable[[], RoleCredentials]) -> None:
        self._role_credentials = role_credentials

    def _role_session_token(self) -> str:
        """The role credentials' session token (blocking: one SDK credential resolution).

        Raises:
            RuntimeError: When no role credentials, or no session token, are available.
        """
        token = self._role_credentials().get_frozen_credentials().token
        if not token:
            raise RuntimeError(
                "The AWS role credentials carry no session token, so there is no credential "
                "to present to a peer. Expected temporary task/instance role credentials; "
                "ensure the service runs under its attached role."
            )
        return str(token)

    async def mint(self) -> str:
        """Obtain the credential from the platform, off the event loop."""
        # AWS instance/task role: SigV4 / role credentials issued by the platform.
        return await asyncio.to_thread(self._role_session_token)
