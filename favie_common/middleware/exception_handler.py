"""Exception Handlers
"""

import logging
import sys
import traceback

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def default_error_handler(_: Request, exception: Exception) -> JSONResponse:
    """High level exception handler for all exceptions"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback_details = traceback.format_tb(exc_traceback)

    exception_details = {"type": str(exc_type.__name__), "message": str(exc_value), "traceback": traceback_details}
    logger.exception("Unhandled Internal Server Error", extra={"json_fields": exception_details})
    logger.exception(exception)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Unhandled Internal Server Error"}
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to FastAPI app"""
    app.add_exception_handler(Exception, default_error_handler)
