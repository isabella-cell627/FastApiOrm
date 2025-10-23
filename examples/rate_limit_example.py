import asyncio
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    RateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
    TieredRateLimiter,
    rate_limit,
)

app = FastAPI(title="Rate Limiting Example")

db = Database("sqlite+aiosqlite:///./rate_limit_demo.db")


class ApiCall(Model):
    __tablename__ = "api_calls"

    id: int = IntegerField(primary_key=True)
    endpoint: str = StringField(max_length=200, nullable=False)
    client_ip: str = StringField(max_length=50, nullable=False)
    timestamp = StringField(max_length=100)


app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(requests=10, window=60, strategy="sliding"),
    exclude_paths=["/", "/health", "/stats"],
    include_headers=True
)


tiered_limiter = TieredRateLimiter({
    "free": RateLimitConfig(requests=10, window=60),
    "pro": RateLimitConfig(requests=100, window=60),
    "enterprise": RateLimitConfig(requests=1000, window=60)
})


async def get_db():
    async for session in db.get_session():
        yield session


@app.on_event("startup")
async def startup():
    await db.create_tables()
    print("✅ Database initialized")
    print("🚦 Rate limiting enabled:")
    print("   • Global: 10 requests per 60 seconds (sliding window)")
    print("   • Excluded paths: /, /health, /stats")
    print("   • Headers included in responses")


@app.on_event("shutdown")
async def shutdown():
    await db.close()


html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Rate Limiting Demo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }
        button {
            background: #2196F3;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
        }
        button:hover { background: #0b7dda; }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .rate-info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
            margin: 10px 0;
        }
        .error {
            background: #ffebee;
            border-left-color: #f44336;
            color: #c62828;
        }
        .success {
            background: #e8f5e9;
            border-left-color: #4CAF50;
            color: #2e7d32;
        }
        #response {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
        .meter {
            height: 30px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .meter-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #2196F3);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>🚦 Rate Limiting Demo</h1>
    
    <div class="container">
        <h2>Rate Limit Status</h2>
        <div id="rate-info" class="rate-info">
            <p><strong>Limit:</strong> <span id="limit">-</span> requests per window</p>
            <p><strong>Remaining:</strong> <span id="remaining">-</span> requests</p>
            <p><strong>Reset in:</strong> <span id="reset">-</span> seconds</p>
        </div>
        <div class="meter">
            <div class="meter-fill" id="meter" style="width: 100%">
                <span id="meter-text">100%</span>
            </div>
        </div>
    </div>
    
    <div class="container">
        <h2>Test Endpoints</h2>
        <p>Each button makes an API request. Watch the rate limit counter!</p>
        
        <div>
            <button onclick="testEndpoint('/api/public')">Public Endpoint (Global Limit)</button>
            <button onclick="testEndpoint('/api/strict')">Strict Endpoint (5/min)</button>
            <button onclick="testEndpoint('/api/tiered/free')">Free Tier (10/min)</button>
            <button onclick="testEndpoint('/api/tiered/pro')">Pro Tier (100/min)</button>
        </div>
        
        <div style="margin-top: 15px;">
            <button onclick="rapidFire()" id="rapid-btn">Rapid Fire (10 requests)</button>
            <button onclick="clearResponse()">Clear Response</button>
        </div>
    </div>
    
    <div class="container">
        <h2>Response Log</h2>
        <div id="response"></div>
    </div>
    
    <script>
        async function testEndpoint(path) {
            const startTime = Date.now();
            
            try {
                const response = await fetch(path);
                const data = await response.json();
                const duration = Date.now() - startTime;
                
                updateRateLimitInfo(response.headers);
                
                if (response.ok) {
                    logResponse('success', path, data, duration);
                } else {
                    logResponse('error', path, data, duration);
                }
            } catch (error) {
                logResponse('error', path, { error: error.message }, 0);
            }
        }
        
        async function rapidFire() {
            const btn = document.getElementById('rapid-btn');
            btn.disabled = true;
            btn.textContent = 'Firing...';
            
            const promises = [];
            for (let i = 0; i < 10; i++) {
                promises.push(testEndpoint('/api/public'));
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            await Promise.all(promises);
            
            btn.disabled = false;
            btn.textContent = 'Rapid Fire (10 requests)';
        }
        
        function updateRateLimitInfo(headers) {
            const limit = headers.get('X-RateLimit-Limit');
            const remaining = headers.get('X-RateLimit-Remaining');
            const reset = headers.get('X-RateLimit-Reset');
            
            if (limit && remaining) {
                document.getElementById('limit').textContent = limit;
                document.getElementById('remaining').textContent = remaining;
                document.getElementById('reset').textContent = reset || '0';
                
                const percentage = (parseInt(remaining) / parseInt(limit)) * 100;
                const meter = document.getElementById('meter');
                const meterText = document.getElementById('meter-text');
                
                meter.style.width = percentage + '%';
                meterText.textContent = Math.round(percentage) + '%';
                
                if (percentage < 20) {
                    meter.style.background = 'linear-gradient(90deg, #f44336, #e91e63)';
                } else if (percentage < 50) {
                    meter.style.background = 'linear-gradient(90deg, #ff9800, #ffc107)';
                } else {
                    meter.style.background = 'linear-gradient(90deg, #4CAF50, #2196F3)';
                }
            }
        }
        
        function logResponse(type, path, data, duration) {
            const responseDiv = document.getElementById('response');
            const entry = document.createElement('div');
            entry.className = `rate-info ${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            entry.innerHTML = `
                <strong>[${timestamp}] ${path}</strong> (${duration}ms)<br>
                ${JSON.stringify(data, null, 2)}
            `;
            
            responseDiv.insertBefore(entry, responseDiv.firstChild);
            
            while (responseDiv.children.length > 20) {
                responseDiv.removeChild(responseDiv.lastChild);
            }
        }
        
        function clearResponse() {
            document.getElementById('response').innerHTML = '';
        }
        
        setInterval(async () => {
            try {
                const response = await fetch('/stats');
                updateRateLimitInfo(response.headers);
            } catch (e) {}
        }, 2000);
    </script>
</body>
</html>
"""


@app.get("/")
async def root():
    return HTMLResponse(html_template)


@app.get("/health")
async def health():
    """Health check endpoint (excluded from rate limiting)"""
    return {"status": "healthy"}


@app.get("/stats")
async def stats(request: Request):
    """Get statistics (excluded from rate limiting)"""
    return {
        "message": "Server stats",
        "timestamp": asyncio.get_event_loop().time()
    }


@app.get("/api/public")
async def public_endpoint(request: Request):
    """Public endpoint with global rate limit (10/min)"""
    return {
        "message": "Public endpoint accessed successfully",
        "rate_limit": "10 requests per 60 seconds (global)"
    }


@app.get("/api/strict")
@rate_limit(requests=5, window=60, strategy="sliding")
async def strict_endpoint(request: Request):
    """Strict endpoint with custom rate limit (5/min)"""
    return {
        "message": "Strict endpoint accessed successfully",
        "rate_limit": "5 requests per 60 seconds (route-specific)"
    }


@app.get("/api/tiered/{tier}")
async def tiered_endpoint(request: Request, tier: str):
    """Tiered endpoint with different limits per user level"""
    if tier not in ["free", "pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    if not await tiered_limiter.is_allowed(request, tier):
        limit_info = tiered_limiter.get_limit_info(request, tier)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {tier} tier",
            headers={
                "X-RateLimit-Limit": str(limit_info['limit']),
                "X-RateLimit-Remaining": str(limit_info['remaining']),
                "X-RateLimit-Reset": str(limit_info['reset'])
            }
        )
    
    tier_limits = {
        "free": "10 requests per 60 seconds",
        "pro": "100 requests per 60 seconds",
        "enterprise": "1000 requests per 60 seconds"
    }
    
    return {
        "message": f"Tiered endpoint accessed with {tier} tier",
        "rate_limit": tier_limits[tier]
    }


async def demo_rate_limiting():
    """
    Standalone demo showing rate limiting functionality.
    """
    print("\n" + "=" * 60)
    print("RATE LIMITING DEMO")
    print("=" * 60 + "\n")
    
    print("🚦 Rate Limiting Strategies:\n")
    
    print("1️⃣  Fixed Window:")
    print("   • Resets counter at fixed intervals")
    print("   • Simpler but less accurate")
    print("   • Can allow 2x limit at boundaries\n")
    
    print("2️⃣  Sliding Window:")
    print("   • Tracks individual request timestamps")
    print("   • More accurate rate limiting")
    print("   • Recommended for most use cases\n")
    
    print("3️⃣  Token Bucket:")
    print("   • Allows burst traffic")
    print("   • Tokens refill at constant rate")
    print("   • Good for APIs with varying load\n")
    
    print("📊 Implementation Options:\n")
    print("   • Global middleware (all routes)")
    print("   • Route-specific decorators")
    print("   • Tiered limits (free/pro/enterprise)")
    print("   • Custom client identification\n")
    
    print("📈 Features:\n")
    print("   ✅ Multiple strategies (fixed, sliding, token bucket)")
    print("   ✅ Per-client tracking")
    print("   ✅ Standard rate limit headers")
    print("   ✅ Customizable client identifiers")
    print("   ✅ Path exclusions")
    print("   ✅ Tiered rate limits\n")
    
    print("=" * 60)
    print("To run the full demo:")
    print("   uvicorn examples.rate_limit_example:app --reload --port 5000")
    print("   Then open: http://localhost:5000")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║          FASTAPI ORM - RATE LIMITING MIDDLEWARE              ║
╚══════════════════════════════════════════════════════════════╝

This example demonstrates comprehensive rate limiting features:

✅ Global rate limiting via middleware
✅ Route-specific limits with decorators
✅ Multi-tier rate limits (free/pro/enterprise)
✅ Multiple strategies (fixed, sliding, token bucket)
✅ Real-time rate limit visualization

To run the interactive demo:

    uvicorn examples.rate_limit_example:app --reload --port 5000

Then open your browser to:

    http://localhost:5000

Try the rapid fire button to see rate limiting in action!
    """)
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_rate_limiting())
