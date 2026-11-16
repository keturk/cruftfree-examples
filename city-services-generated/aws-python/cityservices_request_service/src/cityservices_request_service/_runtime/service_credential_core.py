"""Bounded acquisition of a generated service's machine-identity credential.

Emitted verbatim as ``<package>/_runtime/service_credential_core.py`` of every
service that presents a machine-identity credential to a peer. The service's
``_service_credential`` module binds it once, with the minter of its platform's
strategy (one ``_runtime/service_credential_<strategy>`` module), the shared
acquisition bound and the error class the shared vocabulary names.

The credential is the platform's own machine identity, never a self-signed
application token and never a static shared secret. Acquiring it is bounded on
its own: never charged against an outbound call's timeout, and never left
unbounded.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class ServiceCredentialTimeout(Exception):
    """The machine-identity credential was not obtained within its bound.

    Raised instead of a timeout of the call the credential was for, so a caller
    tells "this service could not obtain its credential" apart from "the
    dependency timed out". The service's binding names its concrete subclass.
    """


class BoundedServiceCredential:
    """The one entry point an outbound call awaits for its credential.

    Args:
        mint: Obtains the credential from the platform.
        timeout_seconds: The longest acquiring the credential may take.
        timeout_error: The error raised past the bound.
    """

    def __init__(
        self,
        *,
        mint: Callable[[], Awaitable[str]],
        timeout_seconds: float,
        timeout_error: type[ServiceCredentialTimeout],
    ) -> None:
        self._mint = mint
        self._timeout_seconds = timeout_seconds
        self._timeout_error = timeout_error

    async def acquire(self) -> str:
        """Return the managed machine-identity credential for an outbound call.

        The credential's audience is the machine identity provider's OWN resource,
        resolved by the strategy's minter (the callee validates every service
        credential against the same machine provider, so the audience is a system
        constant, not a per-callee value). It is never the callee's network address.

        Returns:
            The bearer credential string to place on the outbound request.

        Raises:
            ServiceCredentialTimeout: The bound's subclass, when the credential is not
                obtained within the bound.
            RuntimeError: When the platform credential cannot be obtained.
        """
        try:
            return await asyncio.wait_for(self._mint(), timeout=self._timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise self._timeout_error(
                "The machine-identity credential was not obtained within "
                f"{self._timeout_seconds}s. Expected the platform credential "
                "endpoint to answer; check its reachability from this service."
            ) from exc
