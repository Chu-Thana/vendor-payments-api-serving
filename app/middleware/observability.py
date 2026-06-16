from __future__ import annotations

import json
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger("vendor_payments_api")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        start_time = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            process_time_ms = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                json.dumps(
                    {
                        "event": "api_request_error",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "process_time_ms": process_time_ms,
                    }
                )
            )
            raise

        process_time_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-MS"] = str(process_time_ms)

        logger.info(
            json.dumps(
                {
                    "event": "api_request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": process_time_ms,
                }
            )
        )

        return response