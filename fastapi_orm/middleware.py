"""
Middleware utilities for FastAPI ORM.

This module provides middleware for automatic request logging, tracing,
performance monitoring, and error tracking.

Features:
- Request/response logging
- Execution time tracking
- Request ID generation
- Database query tracking
- Error logging and tracking
- Custom headers injection

Example:
    ```python
    from fastapi import FastAPI
    from fastapi_orm.middleware import (
        RequestLoggingMiddleware,
        PerformanceMiddleware,
        RequestIDMiddleware
    )
    
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(RequestLoggingMiddleware, log_body=True)
    ```
"""

import time
import uuid
import logging
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import json


logger = logging.getLogger("fastapi_orm.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and inject unique request IDs.
    
    Adds a unique ID to each request for tracking and correlation.
    The ID is available in request.state.request_id and in response headers.
    
    Example:
        ```python
        from fastapi import FastAPI, Request
        
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        
        @app.get("/")
        async def root(request: Request):
            return {"request_id": request.state.request_id}
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID"
    ):
        """
        Initialize RequestID middleware.
        
        Args:
            app: ASGI application
            header_name: Header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and inject request ID."""
        # Generate or use existing request ID
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers[self.header_name] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.
    
    Logs details about each request including method, path, status code,
    execution time, and optionally request/response bodies.
    
    Example:
        ```python
        app.add_middleware(
            RequestLoggingMiddleware,
            log_body=True,
            log_headers=False,
            exclude_paths=["/health", "/metrics"]
        )
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_body: bool = False,
        log_headers: bool = False,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        Initialize request logging middleware.
        
        Args:
            app: ASGI application
            log_body: Whether to log request/response bodies
            log_headers: Whether to log headers
            exclude_paths: Paths to exclude from logging
        """
        super().__init__(app)
        self.log_body = log_body
        self.log_headers = log_headers
        self.exclude_paths = set(exclude_paths or [])
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process and log request."""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get request ID if available
        request_id = getattr(request.state, "request_id", "N/A")
        
        # Start timer
        start_time = time.time()
        
        # Log request
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client": request.client.host if request.client else None,
        }
        
        if self.log_headers:
            log_data["headers"] = dict(request.headers)
        
        # Log request body if enabled (preserve body for downstream)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        log_data["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        log_data["body"] = body.decode()[:500]  # Limit size
                
                # Re-inject body by creating a new receive function
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
            except Exception:
                pass
        
        logger.info(f"Request: {json.dumps(log_data)}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        response_log = {
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(log_level, f"Response: {json.dumps(response_log)}")
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request performance.
    
    Adds performance metrics to response headers and logs slow requests.
    
    Example:
        ```python
        app.add_middleware(
            PerformanceMiddleware,
            slow_request_threshold=1.0,  # 1 second
            add_headers=True
        )
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = 1.0,
        add_headers: bool = True
    ):
        """
        Initialize performance middleware.
        
        Args:
            app: ASGI application
            slow_request_threshold: Threshold in seconds for slow request warning
            add_headers: Whether to add performance headers to response
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.add_headers = add_headers
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and track performance."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # Add performance headers if enabled
        if self.add_headers:
            response.headers["X-Process-Time"] = str(round(duration_ms, 2))
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            request_id = getattr(request.state, "request_id", "N/A")
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (request_id: {request_id})"
            )
        
        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking and logging application errors.
    
    Catches exceptions, logs them with context, and returns proper error responses.
    
    Example:
        ```python
        app.add_middleware(
            ErrorTrackingMiddleware,
            include_trace=True,
            notify_on_error=lambda error: send_to_sentry(error)
        )
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        include_trace: bool = False,
        notify_on_error: Optional[Callable] = None
    ):
        """
        Initialize error tracking middleware.
        
        Args:
            app: ASGI application
            include_trace: Include stack trace in response (dev only!)
            notify_on_error: Callback function for error notifications
        """
        super().__init__(app)
        self.include_trace = include_trace
        self.notify_on_error = notify_on_error
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and catch errors."""
        try:
            response = await call_next(request)
            return response
        
        except Exception as exc:
            # Get request context
            request_id = getattr(request.state, "request_id", "N/A")
            
            # Log error with context
            logger.error(
                f"Error processing request: {request.method} {request.url.path} "
                f"(request_id: {request_id})",
                exc_info=True
            )
            
            # Notify if callback provided
            if self.notify_on_error:
                try:
                    await self.notify_on_error(exc)
                except Exception:
                    pass
            
            # Return error response
            from fastapi.responses import JSONResponse
            
            error_response = {
                "error": "Internal Server Error",
                "message": str(exc) if self.include_trace else "An error occurred",
                "request_id": request_id
            }
            
            if self.include_trace:
                import traceback
                error_response["trace"] = traceback.format_exc()
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )


class CORSHeadersMiddleware(BaseHTTPMiddleware):
    """
    Simple CORS headers middleware.
    
    For production use, consider fastapi.middleware.cors.CORSMiddleware instead.
    
    Example:
        ```python
        app.add_middleware(
            CORSHeadersMiddleware,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"]
        )
        ```
    """
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] = ["*"],
        allow_methods: list[str] = ["*"],
        allow_headers: list[str] = ["*"],
        allow_credentials: bool = True
    ):
        """
        Initialize CORS middleware.
        
        Args:
            app: ASGI application
            allow_origins: Allowed origins
            allow_methods: Allowed HTTP methods
            allow_headers: Allowed headers
            allow_credentials: Allow credentials
        """
        super().__init__(app)
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers
        self.allow_credentials = allow_credentials
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and add CORS headers."""
        response = await call_next(request)
        
        origin = request.headers.get("origin")
        
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


__all__ = [
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "PerformanceMiddleware",
    "ErrorTrackingMiddleware",
    "CORSHeadersMiddleware",
]
