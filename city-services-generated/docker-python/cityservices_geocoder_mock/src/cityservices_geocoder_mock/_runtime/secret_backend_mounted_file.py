"""A mounted secrets directory as a generated service's secret backend.

Emitted verbatim as ``<package>/_runtime/secret_backend_mounted_file.py`` beside
``secret_resolver_core`` for a service whose secret backend is ``file`` or
``docker-secret``: each secret is the file ``<secrets dir>/<rendered name>``. A
file read only; no environment variable is consulted.
"""

from __future__ import annotations

import os
from typing import Protocol

from .secret_resolver_core import SecretReferences

#: The trailing line break a mounted secret file carries, which is not part of the value.
_LINE_BREAK = "\n"

#: Encoding every mounted secret file is read in.
_SECRET_FILE_ENCODING = "utf-8"


class SecretsDirectoryBootstrap(Protocol):
    """What the fetch reads from the service's ``config._bootstrap`` module.

    The generated bootstrap module satisfies it. The directory is read on every
    fetch, never captured at bind time.
    """

    @property
    def SECRETS_DIR_PATH(self) -> str | None:
        """The directory the deployment mounts the service's secret files in."""


class MountedFileSecrets:
    """Reads secrets from the files of a mounted secrets directory.

    Args:
        references: The service's secret manifest; a handle's rendered name is its
            file's leaf name.
        bootstrap: The service's ``config._bootstrap`` module, whose baked
            ``SECRETS_DIR_PATH`` names the directory.
    """

    def __init__(
        self, references: SecretReferences, *, bootstrap: SecretsDirectoryBootstrap
    ) -> None:
        self._references = references
        self._bootstrap = bootstrap

    async def fetch(self, handle: str) -> str | None:
        """The contents of *handle*'s file, without its trailing line break.

        Returns:
            The file contents, or ``None`` when the file is absent. Never logged.

        Raises:
            KeyError: *handle* is not declared in the manifest.
            RuntimeError: The bootstrap carries no secrets directory.
        """
        leaf = self._references.rendered_name(handle)
        secrets_dir = self._bootstrap.SECRETS_DIR_PATH
        if not secrets_dir:
            raise RuntimeError(
                "Secret handle %r cannot be read: the service's bootstrap has no "
                "SECRETS_DIR_PATH. Expected generation to bake the mounted secrets "
                "directory for a file or docker-secret backend. Regenerate the service "
                "with a resolved secrets directory." % handle
            )
        secret_path = os.path.join(secrets_dir, leaf)
        try:
            with open(secret_path, encoding=_SECRET_FILE_ENCODING) as fh:
                value = fh.read().rstrip(_LINE_BREAK)
        except FileNotFoundError:
            return None
        return value
