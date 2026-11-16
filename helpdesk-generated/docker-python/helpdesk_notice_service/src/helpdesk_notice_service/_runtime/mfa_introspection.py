"""Second-factor proof read from a provider's RFC 7662 introspection answer.

Emitted verbatim as ``<package>/_runtime/mfa_introspection.py`` beside ``identity_core``
of every service that validates provider tokens. It serves a provider whose access
tokens carry no authentication methods but whose introspection answer does (a
self-hosted Zitadel): the plan's ``mfaFactorProof.source`` is ``introspection`` and
``mfaFactorProof.introspection`` names where to ask. The core calls
:meth:`FactorIntrospection.proves` for such a token after it has verified signature,
issuer, audience and expiry.

The question is signed, not secret-bearing: the client authenticates with a short-lived
RS256 assertion (RFC 7523) signed by the private key the provisioning job wrote for this
provider, so no reusable client secret exists to leak. The key file is read at every
question, so a key rotated by a later provisioning run is picked up without a restart.

Only an answer that is ``active``, names the verified token's own subject, and whose
authentication methods hold a proving value is a proof, and only a proof is cached, for
at most the plan's ``cacheSeconds`` and never past the token's ``exp``. Anything that
cannot be read (no key file, a transport error, a status other than 200, a body that is
not a JSON object) raises :class:`FactorIntrospectionUnavailable`; the core refuses the
token either way, so an unreachable provider never admits one.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import OrderedDict
from collections.abc import Callable, Mapping
from pathlib import Path

import jwt

logger = logging.getLogger(__name__)

# Members of the plan's ``mfaFactorProof.introspection`` object.
_ENDPOINT_URL: str = "url"
_ENDPOINT_HOST_HEADER: str = "hostHeader"
_ENDPOINT_CREDENTIAL_FILE: str = "credentialFile"
_ENDPOINT_CACHE_SECONDS: str = "cacheSeconds"

# Members of the key file the provisioning job writes.
_KEY_ID: str = "keyId"
_KEY_PRIVATE: str = "key"
_KEY_CLIENT_ID: str = "clientId"

# Members of the RFC 7662 answer the check reads.
_ANSWER_ACTIVE: str = "active"
_ANSWER_SUBJECT: str = "sub"

_ASSERTION_ALGORITHM: str = "RS256"
_ASSERTION_LIFETIME_SECONDS: int = 60
_CLIENT_ASSERTION_TYPE: str = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
_HTTP_OK: int = 200
_HOST_HEADER_NAME: str = "Host"


class FactorIntrospectionUnavailable(Exception):
    """The provider's answer about a token could not be obtained or read.

    The message names the step that failed, never a token, a key or a response body.
    """


class FactorIntrospection:
    """The introspection question of a service, with its cache of proving answers.

    Args:
        timeout_seconds: Timeout of one introspection request.
        cache_max_entries: Upper bound on the in-process cache of proving answers.
    """

    def __init__(self, *, timeout_seconds: int, cache_max_entries: int) -> None:
        self._timeout_seconds = timeout_seconds
        self._cache_max_entries = cache_max_entries
        #: ``sha256(token)`` -> expiry (epoch seconds) of a proving answer, least recently used first.
        self._proofs: OrderedDict[str, float] = OrderedDict()

    def _cached(self, key: str) -> bool:
        expires = self._proofs.get(key)
        if expires is None:
            return False
        if expires <= time.time():
            del self._proofs[key]
            return False
        self._proofs.move_to_end(key)
        return True

    def _remember(self, key: str, expires: float) -> None:
        self._proofs[key] = expires
        self._proofs.move_to_end(key)
        while len(self._proofs) > self._cache_max_entries:
            self._proofs.popitem(last=False)

    async def proves(
        self,
        *,
        token: str,
        claims: Mapping[str, object],
        issuer: str,
        endpoint: Mapping[str, object],
        proving: Callable[[Mapping[str, object]], bool],
    ) -> bool:
        """Whether the provider's answer about *token* proves a second factor.

        Args:
            token: The raw bearer token, already verified by the core.
            claims: The verified claims of *token*.
            issuer: The provider's issuer, the audience of the signed assertion.
            endpoint: The plan's ``mfaFactorProof.introspection`` object.
            proving: Reads the proof out of the answer: ``True`` when its authentication
                methods hold a proving value.

        Returns:
            ``True`` for an active answer about this token's own subject that proves the
            factor; ``False`` for an inactive answer, another subject's, or no proof.

        Raises:
            FactorIntrospectionUnavailable: The answer could not be obtained or read.
        """
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if self._cached(key):
            return True
        body = await asyncio.to_thread(self._ask, token, issuer, endpoint)
        if body.get(_ANSWER_ACTIVE) is not True:
            return False
        answered_subject = body.get(_ANSWER_SUBJECT)
        if str(answered_subject) != str(claims.get(_ANSWER_SUBJECT, "")):
            return False
        if not proving(body):
            return False
        cache_seconds = endpoint.get(_ENDPOINT_CACHE_SECONDS)
        if isinstance(cache_seconds, int) and cache_seconds > 0:
            expires = time.time() + cache_seconds
            token_expiry = claims.get("exp")
            if isinstance(token_expiry, (int, float)) and not isinstance(
                token_expiry, bool
            ):
                expires = min(expires, float(token_expiry))
            self._remember(key, expires)
        return True

    def _ask(
        self, token: str, issuer: str, endpoint: Mapping[str, object]
    ) -> dict[str, object]:
        """POST the signed question and return the provider's JSON answer.

        Raises:
            FactorIntrospectionUnavailable: No usable key, a transport failure, a status
                other than 200, or a body that is not a JSON object.
        """
        url = endpoint.get(_ENDPOINT_URL)
        if not isinstance(url, str) or not url:
            raise FactorIntrospectionUnavailable("the plan names no introspection url")
        form = urllib.parse.urlencode(
            {
                "client_assertion_type": _CLIENT_ASSERTION_TYPE,
                "client_assertion": self._assertion(endpoint, issuer),
                "token": token,
                "token_type_hint": "access_token",
            }
        ).encode("ascii")
        request = urllib.request.Request(  # noqa: S310 -- scheme checked when the plan loads
            url,
            data=form,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        host_header = endpoint.get(_ENDPOINT_HOST_HEADER)
        if isinstance(host_header, str) and host_header:
            request.add_unredirected_header(_HOST_HEADER_NAME, host_header)
        try:
            # The URL is the plan's, whose loader refused every scheme but http and https.
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:  # nosec B310
                status = response.status
                raw = response.read()
        except (urllib.error.URLError, OSError) as exc:
            logger.error(
                "factor_introspection_request_failed error=%s", type(exc).__name__
            )
            raise FactorIntrospectionUnavailable(
                "the introspection request failed"
            ) from exc
        if status != _HTTP_OK:
            logger.error("factor_introspection_status_unexpected status=%s", status)
            raise FactorIntrospectionUnavailable(
                "the introspection answer is not HTTP 200"
            )
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise FactorIntrospectionUnavailable(
                "the introspection answer is not JSON"
            ) from exc
        if not isinstance(body, dict):
            raise FactorIntrospectionUnavailable(
                "the introspection answer is not an object"
            )
        return body

    @staticmethod
    def _assertion(endpoint: Mapping[str, object], issuer: str) -> str:
        """The signed client assertion that authenticates the question (RFC 7523).

        Raises:
            FactorIntrospectionUnavailable: The key file is missing, unreadable or does not
                hold ``keyId``, ``key`` and ``clientId``.
        """
        credential_file = endpoint.get(_ENDPOINT_CREDENTIAL_FILE)
        if not isinstance(credential_file, str) or not credential_file:
            raise FactorIntrospectionUnavailable(
                "the plan names no introspection key file"
            )
        try:
            document = json.loads(Path(credential_file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.error(
                "factor_introspection_key_unreadable error=%s", type(exc).__name__
            )
            raise FactorIntrospectionUnavailable(
                "the introspection key file is unreadable"
            ) from exc
        if not isinstance(document, dict) or not all(
            isinstance(document.get(member), str) and document[member]
            for member in (_KEY_ID, _KEY_PRIVATE, _KEY_CLIENT_ID)
        ):
            raise FactorIntrospectionUnavailable(
                "the introspection key file does not hold keyId, key and clientId"
            )
        client_id: str = document[_KEY_CLIENT_ID]
        issued_at = int(time.time())
        return jwt.encode(
            {
                "iss": client_id,
                "sub": client_id,
                "aud": issuer,
                "iat": issued_at,
                "exp": issued_at + _ASSERTION_LIFETIME_SECONDS,
                "jti": uuid.uuid4().hex,
            },
            document[_KEY_PRIVATE],
            algorithm=_ASSERTION_ALGORITHM,
            headers={"kid": document[_KEY_ID]},
        )
