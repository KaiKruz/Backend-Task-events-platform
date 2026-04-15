from __future__ import annotations

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_default_exception_handler


def _best_code(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "validation_error"
    if isinstance(exc, APIException):
        return str(getattr(exc, "default_code", "error"))
    return "error"


def drf_exception_handler(exc: Exception, context):
    """
    Normalize all DRF errors into the assignment envelope:
    { "detail": <string|object>, "code": <string> }
    """
    response = drf_default_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        detail = detail["detail"]

    response.data = {"detail": detail, "code": _best_code(exc)}
    return response

