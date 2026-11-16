"""Exception handlers that map exceptions to RFC 7807 Problem Details.

``problem_for_exception`` is the one mapping from a raised exception to the problem
it is answered as. The FastAPI application registers a handler for every mapped
class (``register_error_handlers``), and every serverless HTTP adapter (AWS
Lambda, Azure Functions) answers a handler's failure through the same function,
so a declaration answers the same status and body whether a REST route or a
serverless route serves it. ``is_retryable_failure`` reads the status the same
mapping gives an exception, so an endpoint ``@retry`` re-runs a handler only for
a server error and never for a deliberate client-error answer.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cityservices_geocoder_mock.auth import AuthorizationDenied
from cityservices_geocoder_mock.errors.problem_details import (
    problem_response,
    problem_status,
    problem_title,
    request_validation_response,
    status_problem_response,
)
from cityservices_geocoder_mock.request_context import MissingTenantRefusal
from cityservices_geocoder_mock.services._base import (
    CascadeRestrictionError,
    EntityNotFoundError,
)
from cityservices_geocoder_mock.services._base import (
    ValidationError as ServiceValidationError,
)

logger = logging.getLogger(__name__)

#: Builds the problem one mapped exception is answered as, naming the request
#: path (or a serverless route template) as the problem's ``instance``.
ProblemFactory = Callable[[Exception, str], JSONResponse]

#: The HTTP status one mapped exception is answered with, read without building
#: (or logging) the answer.
StatusOf = Callable[[Exception], int]

MappedException = TypeVar("MappedException", bound=Exception)

#: The lowest status a failure an endpoint ``@retry`` re-runs may answer with.
_RETRYABLE_STATUS_MIN = 500


def _family_status(family: str) -> StatusOf:
    """The status of an exception always answered as the registered *family*."""

    def status_of(_exc: Exception) -> int:
        return problem_status(family)

    return status_of


def _http_exception_status(exc: Exception) -> int:
    return cast(StarletteHTTPException, exc).status_code


# The one client-visible detail of every authorization denial -- identical to
# the auth dependencies' own 403, so a denial never discloses why.
_FORBIDDEN_DETAIL = "Insufficient permissions"


def _entity_not_found_problem(exc: EntityNotFoundError, instance: str) -> JSONResponse:
    return problem_response("entity-not-found", instance=instance, detail=str(exc))


def _cascade_restriction_problem(
    exc: CascadeRestrictionError, instance: str
) -> JSONResponse:
    return problem_response("cascade-restriction", instance=instance, detail=str(exc))


def _service_validation_problem(
    exc: ServiceValidationError, instance: str
) -> JSONResponse:
    # The declared messages of every rule that failed, in declaration order.
    return problem_response(
        "validation",
        instance=instance,
        detail=problem_title("validation"),
        violations=list(exc.errors),
    )


def _request_validation_problem(
    exc: RequestValidationError, instance: str
) -> JSONResponse:
    return request_validation_response(exc.errors(), instance=instance)


def _http_exception_problem(exc: StarletteHTTPException, instance: str) -> JSONResponse:
    """A bare-status HTTPException (auth guards, rate limiting, clients) answers as
    Problem Details too, keeping any headers the raiser set (Retry-After,
    WWW-Authenticate)."""
    return status_problem_response(
        exc.status_code,
        instance=instance,
        detail=str(exc.detail),
        headers=exc.headers,
    )


def _missing_tenant_problem(exc: MissingTenantRefusal, instance: str) -> JSONResponse:
    """A request refused for want of a resolved tenant: the registered ``missing-tenant``
    family (401), so a client tells a valid credential with no tenant from a bad
    credential by ``type``. Keeps the ``WWW-Authenticate`` header the refusal carries."""
    return problem_response(
        "missing-tenant",
        instance=instance,
        headers=exc.headers,
    )


def _authorization_denied_problem(
    exc: AuthorizationDenied, instance: str
) -> JSONResponse:
    """A verified principal the contract refuses, raised from handler code (e.g.
    Auth.token() on a principal holding no bearer token) rather than from the auth
    dependencies, which answer their own denials. The body is the same opaque 403
    every authorization denial answers with; the reason code is logged, never
    returned."""
    logger.warning(
        "authorization_denied reason_code=%s path=%s", exc.reason_code, instance
    )
    return problem_response("forbidden", instance=instance, detail=_FORBIDDEN_DETAIL)


def _unhandled_problem(exc: Exception, instance: str) -> JSONResponse:
    """Any other exception: the registered internal problem, with the exception and
    its stack in the log and none of it in the response."""
    logger.error("unhandled_error path=%s", instance, exc_info=exc)
    return problem_response("internal", instance=instance)


def _mapped(
    exception_class: type[MappedException],
    factory: Callable[[MappedException, str], JSONResponse],
    status_of: StatusOf,
) -> tuple[type[Exception], tuple[ProblemFactory, StatusOf]]:
    """One ``_PROBLEM_MAPPINGS`` entry: the answer's factory and its status. Both
    are only ever called with an instance of their own class: the lookups resolve
    the raised exception's MRO."""
    return exception_class, (cast(ProblemFactory, factory), status_of)


#: Every exception class with a mapped problem, with the status that problem
#: carries. ``problem_for_exception`` resolves a raised exception through its MRO,
#: so a subclass answers as its nearest mapped ancestor -- the lookup Starlette's
#: own handler dispatch performs.
_PROBLEM_MAPPINGS: dict[type[Exception], tuple[ProblemFactory, StatusOf]] = dict(
    (
        _mapped(
            EntityNotFoundError,
            _entity_not_found_problem,
            _family_status("entity-not-found"),
        ),
        _mapped(
            CascadeRestrictionError,
            _cascade_restriction_problem,
            _family_status("cascade-restriction"),
        ),
        _mapped(
            ServiceValidationError,
            _service_validation_problem,
            _family_status("validation"),
        ),
        _mapped(
            RequestValidationError,
            _request_validation_problem,
            _family_status("request-validation"),
        ),
        _mapped(
            StarletteHTTPException, _http_exception_problem, _http_exception_status
        ),
        _mapped(
            MissingTenantRefusal,
            _missing_tenant_problem,
            _family_status("missing-tenant"),
        ),
        _mapped(
            AuthorizationDenied,
            _authorization_denied_problem,
            _family_status("forbidden"),
        ),
        _mapped(Exception, _unhandled_problem, _family_status("internal")),
    )
)


def _mapping_for(exc: Exception) -> tuple[ProblemFactory, StatusOf]:
    for exception_class in type(exc).__mro__:
        mapping = _PROBLEM_MAPPINGS.get(exception_class)
        if mapping is not None:
            return mapping
    return _PROBLEM_MAPPINGS[Exception]


def problem_for_exception(exc: Exception, instance: str) -> JSONResponse:
    """The problem *exc* is answered as, naming *instance* as the request path.

    A declared domain exception answers its own status, a built-in refusal its
    registered family, and anything else the registered internal problem -- never
    the exception's message.
    """
    factory, _status_of = _mapping_for(exc)
    return factory(exc, instance)


def is_retryable_failure(exc: BaseException) -> bool:
    """Whether an endpoint ``@retry`` may re-run the handler that raised *exc*.

    Only a failure answered with a server error is retried. A deliberate
    client-error answer (a not-found, a validation failure, a refusal) is returned
    at once: re-running the handler cannot change it, and would repeat a write.
    An exception that is not an ``Exception`` (a cancellation) is never retried.
    """
    if not isinstance(exc, Exception):
        return False
    _factory, status_of = _mapping_for(exc)
    return status_of(exc) >= _RETRYABLE_STATUS_MIN


def _handler_of(
    factory: ProblemFactory,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        return factory(exc, request.url.path)

    return handle


def register_error_handlers(app: FastAPI) -> None:
    """Register an exception handler on the FastAPI application for every mapped class."""
    for exception_class, (factory, _status_of) in _PROBLEM_MAPPINGS.items():
        app.add_exception_handler(exception_class, _handler_of(factory))
