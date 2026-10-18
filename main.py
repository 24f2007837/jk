import time
import uuid
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Assigned values
USER_EMAIL = "24f2007837@ds.study.iitm.ac.in"
ALLOWED_ORIGIN_1 = "https://app-wu5i4u.example.com"
ALLOWED_ORIGIN_2 = "https://dash-eq14wx.example.com"  # Exam verification page origin
RATE_LIMIT_B = 15
RATE_LIMIT_WINDOW = 10.0  # seconds

# Middleware 2: Scoped CORS Policy (Explicit origins only, no wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN_1, ALLOWED_ORIGIN_2],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for per-client rate limiting
CLIENT_REQUESTS: Dict[str, List[float]] = defaultdict(list)

# Combined Middleware for Rate Limiting & Request Context Propagation
@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    # 1. Per-client Rate Limiting (skip OPTIONS preflight)
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            timestamps = CLIENT_REQUESTS[client_id]
            # Slide window (keep timestamps within last 10 seconds)
            valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
            CLIENT_REQUESTS[client_id] = valid_timestamps

            if len(valid_timestamps) >= RATE_LIMIT_B:
                return Response(
                    content='{"detail": "Rate limit exceeded"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                )
            CLIENT_REQUESTS[client_id].append(now)

    # 2. Request Context Propagation
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    # Attach request_id to response header
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/ping")
def ping(request: Request):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "email": USER_EMAIL,
        "request_id": req_id
    }
