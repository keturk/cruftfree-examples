"""Checks of the endpoint members a provider plan entry carries, refused at load.

Emitted verbatim as ``<package>/_runtime/plan_endpoint_checks.py`` beside ``identity_core``
of every service that validates provider tokens. A plan member that names an address the
runtime will call -- a signing-key fetch URL, an introspection URL -- and the ``Host``
header presented there are checked here once, so the runtime never calls an endpoint the
plan does not describe exactly.

Every refusal is an :class:`EndpointProblem` naming the member at fault and never its
value: a refused URL may be the credential the check refused.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_FETCH_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})
_HOST_LABEL_PATTERN: str = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_BARE_HOST_HEADER: re.Pattern[str] = re.compile(
    r"(?P<host>%s(?:\.%s)*|\[[0-9A-Fa-f:.]+\])(?::(?P<port>[0-9]{1,5}))?"
    % (_HOST_LABEL_PATTERN, _HOST_LABEL_PATTERN)
)
_MAX_HOST_LENGTH: int = 253
_MIN_PORT: int = 1
_MAX_PORT: int = 65535


class EndpointProblem(Exception):
    """Why a plan member naming an endpoint is unusable.

    The message names the member, never its value.
    """


def _has_whitespace_or_control(value: str) -> bool:
    """True when *value* contains whitespace or an ASCII control character."""
    return any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def check_fetch_url(value: object) -> None:
    """Refuse *value* unless it is a fetchable ``http(s)`` URL.

    Raises:
        EndpointProblem: Naming what is wrong with ``url``.
    """
    if not isinstance(value, str):
        raise EndpointProblem("'url' is not a string")
    if _has_whitespace_or_control(value):
        raise EndpointProblem("'url' contains whitespace or a control character")
    parts = urlsplit(value)
    if parts.scheme.lower() not in _FETCH_URL_SCHEMES:
        raise EndpointProblem("'url' is not an http or https URL")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise EndpointProblem("'url' carries user information")
    if not parts.hostname:
        raise EndpointProblem("'url' names no host")
    if parts.fragment:
        raise EndpointProblem("'url' carries a fragment")
    try:
        _ = parts.port
    except ValueError as exc:
        raise EndpointProblem("'url' has an invalid port") from exc


def check_host_header(value: object) -> None:
    """Refuse *value* unless it is a bare ``host[:port]`` Host header.

    Raises:
        EndpointProblem: Naming what is wrong with ``hostHeader``.
    """
    if not isinstance(value, str):
        raise EndpointProblem("'hostHeader' is not a string")
    match = _BARE_HOST_HEADER.fullmatch(value)
    if match is None or len(match.group("host")) > _MAX_HOST_LENGTH:
        raise EndpointProblem("'hostHeader' is not a bare host[:port]")
    port = match.group("port")
    if port is not None and not _MIN_PORT <= int(port) <= _MAX_PORT:
        raise EndpointProblem(
            "'hostHeader' names a port outside %d-%d" % (_MIN_PORT, _MAX_PORT)
        )
