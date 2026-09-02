"""
Standardized API response helpers.

All views must use these helpers to return consistent JSON responses.
The frontend team can always expect the same envelope shape.

Success:  {"status": "success", "data": {...}}
Error:    {"status": "error",   "message": "...", "errors": {...}}
"""

from rest_framework.response import Response
from rest_framework import status as http_status


def success_response(data=None, message=None, status=http_status.HTTP_200_OK):
    """Return a standardised success envelope."""
    payload = {"status": "success"}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status)


def created_response(data=None, message="Created successfully."):
    """Convenience wrapper for 201 Created."""
    return success_response(data=data, message=message, status=http_status.HTTP_201_CREATED)


def error_response(message="An error occurred.", errors=None, status=http_status.HTTP_400_BAD_REQUEST):
    """Return a standardised error envelope."""
    payload = {"status": "error", "message": message}
    if errors:
        payload["errors"] = errors
    return Response(payload, status=status)
