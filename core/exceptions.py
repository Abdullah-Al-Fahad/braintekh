"""
Global DRF exception handler.

Converts all exceptions — including Django's validation errors and
unexpected server errors — into our standardised response envelope.
"""

import logging

from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to return consistent JSON.

    All responses follow the shape:
        {"status": "error", "message": "...", "errors": {...}}
    """
    # Let DRF handle the exception first to get its response
    response = exception_handler(exc, context)

    if response is not None:
        error_message = "An error occurred."
        errors = None

        data = response.data

        # DRF validation errors are dicts or lists
        if isinstance(data, dict):
            # Flatten the common "detail" key used by DRF
            if "detail" in data and len(data) == 1:
                error_message = str(data["detail"])
            else:
                error_message = "Validation failed."
                errors = data
        elif isinstance(data, list):
            error_message = "Validation failed."
            errors = {"non_field_errors": data}

        response.data = {
            "status": "error",
            "message": error_message,
        }
        if errors:
            response.data["errors"] = errors

    else:
        # Unhandled server-side exception — log it and return 500
        logger.exception("Unhandled server error: %s", exc)
        response = Response(
            {"status": "error", "message": "An unexpected error occurred. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
