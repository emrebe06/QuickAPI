# QuickAPI

**Write Python. Run Native. Return JSON.**

QuickAPI is a lightweight JSON-first API runtime with a Python developer layer and a future-ready C/C++ native core. It is designed for ecommerce APIs, mobile backends, AI tools, local services, native engines, and fast JSON traffic.

QuickAPI is not a FastAPI clone. Decorators are familiar, but the goal is different: QuickAPI standardizes every request and response, exposes clear error objects, keeps the developer surface small, and prepares hot paths for a native C/C++ core.

## Features

- JSON-first request and response model
- Standard success and error response format
- `QuickAPI` app object with `@app.get`, `@app.post`, `@app.put`, `@app.patch`, `@app.delete`
- `q` response factory for consistent API output
- CLI runner similar to `uvicorn`: `quickapi run main:app --host 0.0.0.0 --port 8000`
- Built-in lightweight docs at `/docs`, `/quick`, and `/openapi.json`
- Request object injection: `body`, `query`, `headers`, `request`, `ml`
- ML guard with intent classification, request feature extraction, anomaly signals, risk scoring, bot scoring, and action policy
- Streaming file responses through `FileResponse`, `app.file()`, and `app.static_file()`
- Built-in job queue for long-running work with `202 Accepted`, `job_id`, status, and cancel endpoints
- Ecommerce response presets
- C/C++ native core starter with CMake and security/risk hotpath helpers
- Native endpoint bridge through `ctypes`
- Basic security guard: CORS, JSON content-type checks, request size limit, rate limiting
- Nginx-friendly listener with `X-Forwarded-For` and `X-Real-IP` support

## Installation

For local development:

```bash
pip install -e .
```

Build package artifacts:

```bash
python -m build
```

The package import name is:

```python
import quickapi
```

The current distribution name is `quickapi-runtime`. If the `quickapi` name is not available on PyPI, possible publish names are `quickapi-core`, `quickapi-runtime`, or `emre-quickapi`.

## Quick Start

```python
from quickapi import QuickAPI, q

app = QuickAPI("My API", docs=True)


@app.get("/ping")
def ping():
    return q.ok({"pong": True})


@app.post("/echo")
def echo(body, request):
    return q.ok({
        "body": body,
        "ip": request.ip,
        "request_id": request.request_id,
    })
```

Run it:

```bash
quickapi run main:app --host 0.0.0.0 --port 8000
```

Local development shortcut:

```bash
quickapi dev main.py --port 8080
```

## Standard JSON Response

Successful responses always follow this shape:

```json
{
  "ok": true,
  "status": 200,
  "code": "OK",
  "message": "Success",
  "data": {},
  "error": null,
  "meta": {
    "request_id": "req_xxx",
    "time_ms": 1.42,
    "engine": "quickapi"
  }
}
```

Error responses always follow this shape:

```json
{
  "ok": false,
  "status": 404,
  "code": "NOT_FOUND",
  "message": "Product not found",
  "data": null,
  "error": {
    "type": "route_error",
    "detail": "No product found with id 42"
  },
  "meta": {
    "request_id": "req_xxx",
    "time_ms": 0.91,
    "engine": "quickapi"
  }
}
```

## Response Factory

```python
q.ok(data, message="Success", status=200)
q.created(data, message="Created")
q.accepted(data, message="Accepted")
q.error(status, code, message, detail=None)
q.not_found(message="Not found")
q.validation(message="Validation error", detail=None)
q.unauthorized(message="Unauthorized")
q.forbidden(message="Forbidden")
q.conflict(message="Conflict")
q.payment_required(message="Payment required")
q.too_many_requests(message="Too many requests")
q.server_error(message="Internal server error")
q.timeout(message="Gateway timeout")
```

## Ecommerce Example

```python
from quickapi import QuickAPI, q
from quickapi.ecommerce import ecommerce_error

app = QuickAPI("Shop API", secure=True, ml=True, docs=True)


@app.post("/cart/add", errors=[409, 422, 429], ml_check=True, rate_limit="strict")
def add_cart(body, ml):
    product_id = body.get("product_id")
    quantity = body.get("quantity", 1)

    if not product_id:
        return q.validation("product_id is required")

    if quantity <= 0:
        return q.validation("quantity must be greater than zero")

    if ml.risk_score > 0.85:
        return q.too_many_requests("Suspicious request blocked")

    if product_id == 42:
        return ecommerce_error.out_of_stock(product_id=42)

    return q.ok({"product_id": product_id, "quantity": quantity})
```

## ML Guard Example

```python
@app.post("/payment/checkout", errors=[402, 422, 429, 504], ml_check=True, rate_limit="strict")
def checkout(body, ml):
    if ml.risk_score > 0.85:
        return q.too_many_requests("Suspicious request blocked", ml.to_dict())
    return q.ok({"payment": "accepted", "ml": ml.to_dict()})
```

The first ML engine is dependency-free and deterministic, but it is no longer a tiny stub. It extracts request features, classifies intent, scores risk and bot-likelihood, flags anomalies, and returns an action policy:

```json
{
  "intent": "payment_attempt",
  "risk_score": 0.92,
  "bot_score": 0.22,
  "action": "block",
  "anomaly": true,
  "confidence": 0.86,
  "reasons": ["sensitive_intent:payment_attempt", "sql_injection"],
  "features": {
    "method": "POST",
    "path_depth": 2,
    "body_bytes": 27,
    "header_count": 3,
    "query_count": 0
  }
}
```

## Streaming Files

Use `app.file()` for downloads and `app.static_file()` for safe static assets:

```python
from pathlib import Path

FILES = Path("storage/converted")


@app.get("/downloads/{file_path:path}")
def download(file_path):
    return app.static_file(FILES, file_path, download=True)
```

The listener streams `FileResponse` chunks instead of forcing large files through `read_bytes()`.

## Background Jobs

Long work can be accepted immediately and tracked later:

```python
def heavy_task(value):
    return {"value": value * 2}


@app.post("/work")
def work(body):
    return app.submit_job(heavy_task, body.get("value", 1), name="heavy_task")
```

Built-in job endpoints:

- `GET /quick/jobs`
- `GET /quick/jobs/{job_id}`
- `DELETE /quick/jobs/{job_id}`

## Native Endpoint Example

Python:

```python
app.native_post(
    "/run/analyze",
    library="./librun_engine.so",
    symbol="analyze_run"
)
```

C/C++:

```cpp
extern "C" const char* analyze_run(const char* json_input) {
    return "{\"ok\":true,\"score\":0.42}";
}
```

Native starter build:

```bash
cmake -S quickapi/native -B build/native
cmake --build build/native --config Release
```

Native hotpath helpers are also available through `NativeRuntime` for payload feature count, risk score, and stable request fingerprints.

## CLI

```bash
quickapi run main:app --host 0.0.0.0 --port 8000
quickapi run main.py:app --port 8000
quickapi run examples.basic_api.main:app --reload
quickapi serve main:app
quickapi dev examples/basic_api/main.py
quickapi routes examples.basic_api.main:app
quickapi docs examples.basic_api.main:app
quickapi bench examples.basic_api.main:app --route /ping --iterations 1000
quickapi new my_api
```

The listener prints access logs and error details:

```text
[quickapi] 127.0.0.1 GET /ping -> 200 OK 0.34ms req=req_xxx
[quickapi] 127.0.0.1 GET /missing -> 404 NOT_FOUND 0.21ms req=req_xxx
[quickapi] error type=route_error detail=No route found for GET /missing
```

## Architecture

```text
quickapi/
  app/         Python developer layer
  routing/     Route metadata and dispatch
  http/        Request, headers, methods, status
  response/    JSON response formatting and q factory
  security/    CORS, rate limit, guard checks
  ml/          Intent/risk/anomaly engine stubs
  ecommerce/   Ecommerce response presets
  server/      HTTP listener and access logs
  bridge/      Python to native bridge
  native/      C/C++ core starter
  cli/         quickapi command line interface
```

Python is the intelligence and developer-experience layer. C/C++ is the future speed layer for route matching, JSON formatting, security hot paths, metrics, and native endpoint execution.

## Nginx

Bind QuickAPI locally:

```bash
quickapi run main:app --host 127.0.0.1 --port 8000
```

Proxy from nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Testing

```bash
python -m pytest
```

## Roadmap

- Native route matching bridge from Python
- Native JSON parse/stringify hot path
- Structured JSON logs
- Development reload improvements
- More complete OpenAPI schema generation
- Production worker model
- Optional ASGI adapter without depending on external frameworks

## License And Rights

Copyright (C) 2026 Emre B.

QuickAPI is licensed under the GNU General Public License version 3.0 only (`GPL-3.0-only`).

You may use, study, modify, and distribute this project under the terms of GPL-3.0. Any distributed derivative work must preserve the same GPL-3.0 license terms and include the required license notices.

This project name, architecture direction, source code, documentation, and original project materials are authored and owned by Emre B. unless a file explicitly states otherwise.
