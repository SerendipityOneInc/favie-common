"""
log HTTP request info to Cloud Logging
"""

import logging
import sys
from datetime import datetime

from fastapi import status
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class HttpLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = datetime.now()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except HTTPException as exc:
            status_code = exc.status_code
            response = Response(status_code=status_code, content=str(exc.detail))
            self.log_request(request, status_code, start_time, response)
            raise exc
        except Exception as exc:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            response = Response(status_code=status_code, content=str(exc))
            self.log_request(request, status_code, start_time, response)
            raise exc
        else:
            self.log_request(request, status_code, start_time, response)
        return response

    def log_request(self, request: Request, status_code: int, start_time: datetime, response: Response):
        end_time = datetime.now()
        http_elapsed_time_ms = (end_time - start_time).total_seconds() * 1000
        http_elapsed_time_ms = round(http_elapsed_time_ms, 2)

        http_request = {
            "request_method": request.method,
            "request_url": request.url.path,
            "request_size": sys.getsizeof(request),
            "remote_ip": request.client.host,
            "protocol": request.url.scheme,
            "params": dict(request.query_params),
        }

        headers_to_log = ["referrer", "user-agent", "Content-Type", "Copilot-Version"]
        for header in headers_to_log:
            if header in request.headers:
                http_request[header] = request.headers.get(header)

        http_response = {
            "status": status_code,
            "response_size": sys.getsizeof(response),
        }

        if "Content-Type" in response.headers:
            http_response["content_type"] = response.headers.get("Content-Type")

        # bypass health check requests
        if request.url.path != "/" and request.url.path != "/admin/metrics":
            logger.info(
                f"Handled HTTP request {request.url.path}",
                extra={
                    "http_request": http_request,
                    "json_fields": {"http_response": http_response, "http_elapsed_time_ms": http_elapsed_time_ms},
                },
            )
