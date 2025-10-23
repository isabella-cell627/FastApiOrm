import pytest
import asyncio

pytest.importorskip("httpx", reason="httpx is required for middleware tests")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi_orm.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    PerformanceMiddleware,
    ErrorTrackingMiddleware,
    CORSHeadersMiddleware
)


@pytest.fixture
def app():
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    return app


def test_request_id_middleware(app):
    app.add_middleware(RequestIDMiddleware)
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_request_id_middleware_custom_header(app):
    app.add_middleware(RequestIDMiddleware, header_name="X-Custom-Request-ID")
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert "X-Custom-Request-ID" in response.headers


def test_request_id_middleware_preserves_existing():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": request.state.request_id}
    
    client = TestClient(app)
    response = client.get("/test", headers={"X-Request-ID": "existing-id"})
    
    data = response.json()
    assert data["request_id"] == "existing-id"


def test_performance_middleware(app):
    app.add_middleware(PerformanceMiddleware)
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers


def test_performance_middleware_slow_request():
    app = FastAPI()
    app.add_middleware(PerformanceMiddleware, slow_request_threshold=0.001)
    
    @app.get("/slow")
    async def slow_endpoint():
        await asyncio.sleep(0.01)
        return {"message": "slow"}
    
    client = TestClient(app)
    response = client.get("/slow")
    
    assert "X-Process-Time" in response.headers
    process_time = float(response.headers["X-Process-Time"])
    assert process_time > 0.001


def test_error_tracking_middleware(app):
    app.add_middleware(ErrorTrackingMiddleware)
    
    client = TestClient(app)
    response = client.get("/error")
    
    assert response.status_code == 500


def test_cors_headers_middleware(app):
    app.add_middleware(
        CORSHeadersMiddleware,
        allow_origins=["http://example.com"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"]
    )
    
    client = TestClient(app)
    response = client.get("/test", headers={"Origin": "http://example.com"})
    
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://example.com"


def test_cors_headers_middleware_wildcard(app):
    app.add_middleware(
        CORSHeadersMiddleware,
        allow_origins=["*"]
    )
    
    client = TestClient(app)
    response = client.get("/test", headers={"Origin": "http://any-origin.com"})
    
    assert "Access-Control-Allow-Origin" in response.headers


def test_multiple_middleware_stack():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(PerformanceMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_request_logging_middleware():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware, log_body=False)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
