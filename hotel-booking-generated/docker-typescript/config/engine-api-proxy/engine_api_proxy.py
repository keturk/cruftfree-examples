"""A read-only, field-filtered view of the container engine's API for the stack's observers.

This module is **emitted verbatim into every compose project that runs a container
observer** (cAdvisor, Promtail) as ``config/engine-api-proxy/engine_api_proxy.py``
(``verbatim_runtime_source``) and imported by its generator, so the program the proxy
container runs is unit tested by calling it. Standard library only.

Why it exists
-------------
cAdvisor names containers, and Promtail discovers them and reads their logs, through the
engine API. The engine socket controls the engine itself: whoever can connect to it can
create a privileged or host-network container, exec into any container, copy files out of
one, and inspect every container's environment, where a platform may hand each service a
secret of its own. A read-only bind of the socket stops none of that. So no observer holds
the socket. This program holds it, alone, and serves the observers only the calls they
make:

* ``GET`` (and ``HEAD`` on the ping) on the routes in :data:`ROUTES`, each with the query
  parameters that route documents. Any other method, path or parameter, and any
  percent-encoded or dot-segment path, is refused with 403 before the engine is asked.
* A container list, a container inspect and a network list are rebuilt from a field
  allowlist (:data:`CONTAINER_INSPECT_FIELDS` and its siblings) holding exactly what the
  observers read. A container's environment, mounts and command, and every field a later
  engine adds, never leave the engine.
* Logs are streamed through unchanged: shipping them is what Promtail is for.

The allowlists follow what the pinned observers read: cAdvisor's Docker handler reads a
container's name, creation and start times, labels, image, restart count, process id,
running state, exit code, health status, network mode and network addresses; Promtail
reads only whether the container has a TTY, and its discovery reads the list's names,
ids, labels, ports, network mode and networks, and the network list's ids, names, scopes,
labels and internal and ingress flags.
"""

from __future__ import annotations

import argparse
import http.client
import json
import logging
import re
import socket
import sys
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

#: The engine socket this program alone is handed, and where it serves the observers.
ENGINE_SOCKET = "/var/run/docker.sock"
#: Every address of the proxy container: its one network is internal and joined only by
#: the observers, so nothing else can reach this port.
LISTEN_ADDRESS = "0.0.0.0"  # nosec B104
LISTEN_PORT = 2375

#: How long a non-streaming engine call may take, and the health probe's own call.
ENGINE_TIMEOUT_SECONDS = 30
PROBE_TIMEOUT_SECONDS = 5

#: The engine answers on its own name; any value is accepted on a unix socket.
_ENGINE_HOST = "docker"

#: An API version prefix (``/v1.43``) the clients put before every path but the ping.
_VERSION_PREFIX = re.compile(r"/v[0-9]{1,2}\.[0-9]{1,3}(?=/)")
#: The characters a path may hold: no percent-encoding, so no encoded separator.
_PLAIN_PATH = re.compile(r"[A-Za-z0-9/_.-]+")
#: A container named in a path: its id or its name.
_CONTAINER = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"

#: The response headers relayed to the observers; the API version header is what their
#: clients negotiate the version from.
_RELAYED_HEADERS = ("Content-Type", "Api-Version", "Docker-Experimental", "Ostype", "Server")

_STREAM_READ_BYTES = 65536


class Body(Enum):
    """How a route's response body reaches the observer."""

    #: Relayed as the engine sent it: it describes the engine, never a container.
    WHOLE = "whole"
    #: Rebuilt from the route's field allowlist.
    FILTERED = "filtered"
    #: Relayed as it arrives, for as long as the engine sends it.
    STREAM = "stream"


#: A field allowlist: each kept key maps to ``None`` (its value kept whole) or to the
#: allowlist of its value. The key ``*`` stands for every key of a mapping keyed by name.
FieldAllowlist = Mapping[str, "FieldAllowlist | None"]

#: A container's attachment to each network it is on.
_NETWORK_ATTACHMENTS: FieldAllowlist = {"*": {"IPAddress": None, "NetworkID": None}}

CONTAINER_INSPECT_FIELDS: FieldAllowlist = {
    "Id": None,
    "Name": None,
    "Created": None,
    "Image": None,
    "RestartCount": None,
    "State": {
        "Status": None,
        "Running": None,
        "Pid": None,
        "ExitCode": None,
        "StartedAt": None,
        "Health": {"Status": None},
    },
    "Config": {"Image": None, "Labels": None, "Tty": None},
    "HostConfig": {"NetworkMode": None},
    "NetworkSettings": {"Networks": _NETWORK_ATTACHMENTS},
}

CONTAINER_LIST_FIELDS: FieldAllowlist = {
    "Id": None,
    "Names": None,
    "Image": None,
    "Created": None,
    "State": None,
    "Status": None,
    "Labels": None,
    "Ports": None,
    "HostConfig": {"NetworkMode": None},
    "NetworkSettings": {"Networks": _NETWORK_ATTACHMENTS},
}

NETWORK_LIST_FIELDS: FieldAllowlist = {
    "Id": None,
    "Name": None,
    "Scope": None,
    "Internal": None,
    "Ingress": None,
    "Labels": None,
}

_GET = frozenset({"GET"})


@dataclass(frozen=True, slots=True)
class Route:
    """One engine call the observers may make.

    Attributes:
        pattern: The path, after any API version prefix.
        methods: The methods allowed on it.
        query: The query parameters it may carry, each at most once.
        body: How its response body reaches the observer.
        fields: The field allowlist of a :attr:`Body.FILTERED` body.
    """

    pattern: re.Pattern[str]
    methods: frozenset[str]
    query: frozenset[str]
    body: Body
    fields: FieldAllowlist | None = None


ROUTES: tuple[Route, ...] = (
    Route(re.compile(r"/_ping"), frozenset({"GET", "HEAD"}), frozenset(), Body.WHOLE),
    Route(re.compile(r"/version"), _GET, frozenset(), Body.WHOLE),
    Route(re.compile(r"/info"), _GET, frozenset(), Body.WHOLE),
    Route(
        re.compile(r"/containers/json"),
        _GET,
        frozenset({"all", "limit", "size", "filters"}),
        Body.FILTERED,
        CONTAINER_LIST_FIELDS,
    ),
    Route(
        re.compile(rf"/containers/{_CONTAINER}/json"),
        _GET,
        frozenset({"size"}),
        Body.FILTERED,
        CONTAINER_INSPECT_FIELDS,
    ),
    Route(
        re.compile(rf"/containers/{_CONTAINER}/logs"),
        _GET,
        frozenset({"follow", "stdout", "stderr", "since", "until", "timestamps", "tail", "details"}),
        Body.STREAM,
    ),
    Route(re.compile(r"/networks"), _GET, frozenset({"filters"}), Body.FILTERED, NETWORK_LIST_FIELDS),
)


@dataclass(frozen=True, slots=True)
class Decision:
    """Whether one request is relayed to the engine.

    Attributes:
        route: The route it is relayed on; ``None`` when it is refused.
        reason: Why it is refused; empty when it is not.
    """

    route: Route | None
    reason: str = ""


def _route_path(path: str) -> str | None:
    """*path* without its API version prefix, or ``None`` when it is not a plain path."""
    if not _PLAIN_PATH.fullmatch(path) or ".." in path or "//" in path:
        return None
    prefix = _VERSION_PREFIX.match(path)
    return path[prefix.end():] if prefix else path


def _query_refusal(query: str, route: Route) -> str:
    """Why *query* may not be sent on *route*; empty when it may."""
    try:
        parameters = urllib.parse.parse_qs(query, keep_blank_values=True, strict_parsing=bool(query))
    except ValueError:
        return "The query string does not parse."
    unknown = sorted(set(parameters) - route.query)
    if unknown:
        return f"Query parameter(s) {unknown} are not served on this path."
    if any(len(values) != 1 for values in parameters.values()):
        return "Each query parameter may be given once."
    return ""


def decide(method: str, target: str) -> Decision:
    """Decide whether the request *method* *target* is relayed to the engine."""
    parts = urllib.parse.urlsplit(target)
    if parts.scheme or parts.netloc or parts.fragment:
        return Decision(None, "Only a path and a query are served.")
    route_path = _route_path(parts.path)
    if route_path is None:
        return Decision(None, "The path must be plain: no encoding, no dot segments.")
    route = next((each for each in ROUTES if each.pattern.fullmatch(route_path)), None)
    if route is None:
        return Decision(None, f"{route_path} is not served.")
    if method not in route.methods:
        return Decision(None, f"{method} is not served on {route_path}.")
    refusal = _query_refusal(parts.query, route)
    if refusal:
        return Decision(None, refusal)
    return Decision(route)


def filter_fields(value: object, allowlist: FieldAllowlist) -> object:
    """*value* holding only the fields *allowlist* keeps.

    A list is filtered item by item. A value that is not a mapping where *allowlist*
    expects one is dropped (``None``): only a field the allowlist names leaves the engine.
    """
    if isinstance(value, list):
        return [filter_fields(item, allowlist) for item in value]
    if not isinstance(value, dict):
        return None
    kept: dict[str, object] = {}
    for key, item in value.items():
        if key in allowlist:
            nested = allowlist[key]
        elif "*" in allowlist:
            nested = allowlist["*"]
        else:
            continue
        kept[key] = item if nested is None else filter_fields(item, nested)
    return kept


class EngineConnection(http.client.HTTPConnection):
    """An HTTP connection to the engine over its unix socket."""

    def __init__(self, socket_path: str, timeout: float | None) -> None:
        super().__init__(_ENGINE_HOST, timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        engine = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        engine.settimeout(self.timeout)
        engine.connect(self._socket_path)
        self.sock = engine


#: Opens a connection to the engine, given the timeout of its calls (``None``: none).
ConnectEngine = Callable[[float | None], http.client.HTTPConnection]


def _logger() -> logging.Logger:
    return logging.getLogger("engine_api_proxy")


def _error_body(message: str) -> bytes:
    """An engine-shaped error document."""
    return json.dumps({"message": message}).encode("utf-8")


class EngineApiHandler(BaseHTTPRequestHandler):
    """Relays each allowed call to the engine; :func:`build_server` binds the engine."""

    protocol_version = "HTTP/1.1"

    def connect_engine(self, timeout: float | None) -> http.client.HTTPConnection:
        """A connection to the engine; the class :func:`build_server` makes overrides it."""
        raise http.client.HTTPException("No engine is bound to this handler.")

    def do_GET(self) -> None:
        self._relay()

    def do_HEAD(self) -> None:
        self._relay()

    def do_POST(self) -> None:
        self._relay()

    def do_PUT(self) -> None:
        self._relay()

    def do_DELETE(self) -> None:
        self._relay()

    def do_PATCH(self) -> None:
        self._relay()

    def _relay(self) -> None:
        self.close_connection = True
        decision = decide(self.command, self.path)
        if decision.route is None:
            _logger().warning(
                "engine_api_refused method=%s path=%s reason=%s",
                self.command, self.path, decision.reason,
            )
            self._send(403, _error_body(decision.reason))
            return
        route = decision.route
        engine = self.connect_engine(None if route.body is Body.STREAM else ENGINE_TIMEOUT_SECONDS)
        started = False
        try:
            engine.request(self.command, self.path, headers={"Host": _ENGINE_HOST})
            response = engine.getresponse()
            started = True
            if route.body is Body.STREAM and response.status == 200:
                self._stream(response)
            else:
                self._relay_whole(response, route)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            _logger().warning("engine_api_failed path=%s error=%s", self.path, exc)
            if not started:
                self._send(502, _error_body("The engine did not answer."))
        finally:
            engine.close()

    def _relay_whole(self, response: http.client.HTTPResponse, route: Route) -> None:
        body = response.read()
        if route.body is Body.FILTERED and response.status == 200 and route.fields is not None:
            body = json.dumps(filter_fields(json.loads(body), route.fields)).encode("utf-8")
        self.send_response(response.status)
        self._relay_headers(response)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _stream(self, response: http.client.HTTPResponse) -> None:
        self.send_response(response.status)
        self._relay_headers(response)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        while chunk := response.read1(_STREAM_READ_BYTES):
            self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")

    def _relay_headers(self, response: http.client.HTTPResponse) -> None:
        for name in _RELAYED_HEADERS:
            value = response.getheader(name)
            if value is not None:
                self.send_header(name, value)

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 -- stdlib signature
        # The request line names a path and a query, never a secret.
        _logger().info("engine_api_request %s", format % args)


def build_server(address: tuple[str, int], connect: ConnectEngine) -> ThreadingHTTPServer:
    """A server on *address* relaying the observers' calls to the engine *connect* reaches."""

    class _BoundEngineApiHandler(EngineApiHandler):
        def connect_engine(self, timeout: float | None) -> http.client.HTTPConnection:
            return connect(timeout)

    server = ThreadingHTTPServer(address, _BoundEngineApiHandler)
    server.daemon_threads = True
    return server


def _connect_engine(timeout: float | None) -> http.client.HTTPConnection:
    return EngineConnection(ENGINE_SOCKET, timeout)


def serve() -> None:
    """Serve the observers on :data:`LISTEN_PORT` until stopped."""
    server = build_server((LISTEN_ADDRESS, LISTEN_PORT), _connect_engine)
    _logger().info("engine_api_proxy_serving port=%d engine=%s", LISTEN_PORT, ENGINE_SOCKET)
    server.serve_forever()


def probe(port: int = LISTEN_PORT) -> int:
    """0 when the proxy on *port* relays a ping the engine answers, else 1."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=PROBE_TIMEOUT_SECONDS)
    try:
        connection.request("GET", "/_ping")
        status = connection.getresponse().status
    except (OSError, http.client.HTTPException) as exc:
        _logger().warning("engine_api_probe_failed error=%s", exc)
        return 1
    finally:
        connection.close()
    return 0 if status == 200 else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command: ``serve`` (the proxy) or ``probe`` (its health check)."""
    parser = argparse.ArgumentParser(description="Serve the observers a read-only engine API.")
    parser.add_argument("command", choices=("serve", "probe"))
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if arguments.command == "probe":
        return probe()
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
