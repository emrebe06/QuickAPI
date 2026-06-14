# QuickAPI Security Model

QuickAPI treats security as a layered request pipeline, not as a single middleware.

## Current Layers

1. Listener limits
   - Request body size is checked before JSON parsing.
   - Overload protection returns `503` instead of hanging until timeout.
   - ASGI requests also enforce `max_body_size`.

2. Security guard
   - Rejects suspicious paths, control characters, traversal probes, scanner paths, invalid JSON content type, and basic body attack tokens.
   - Applies simple IP rate limiting when `secure=True`.

3. Schema validation
   - Validates path, query, and body before route handlers run.
   - Supports JSON Schema-style rules such as `$ref`, `oneOf`, `anyOf`, `allOf`, `patternProperties`, `dependentRequired`, and standard schemas such as `openrtb.bid_request`.

4. Native hot-path scan
   - C/C++ scanners can inspect payload size, content type, path, command injection, SQL injection, SSRF, scanner probes, dangerous uploads, and JSON shape signals.
   - Native route matching can mirror Python routes when a native runtime library is loaded.

5. Synaptic / ML Guard
   - Combines rule signals, schema errors, native scan signals, route sensitivity, bot score, anomaly score, and a lightweight trainable model score.
   - Produces an explainable decision report: `allow`, `observe`, `challenge`, or `block`.

6. Auth and permissions
   - Route auth supports bearer tokens or a custom validator.
   - Plugins declare permissions and cannot run privileged actions unless the app grants those permissions.
   - Local tool execution is disabled by default.

## Trust Boundaries

- Python owns developer-facing routes and business logic.
- Native code owns selected hot paths when explicitly loaded.
- `app.native_post(...)` calls a native symbol through `ctypes`; it does not mean the whole server is native.
- The built-in ML model is lightweight and explainable. It is not a large pretrained security model.
- ASGI support is available through `app.asgi()`, while the built-in listener remains sync/threaded.

## Defaults

- `secure=False`
- `ml=False`
- `ml_guard=False`
- `local_tools_enabled=False`
- `agent_backend_enabled=False`
- `plugins_enabled=True`, but plugin permissions must be granted explicitly for privileged plugins.

These defaults favor compatibility and local development. Public services should enable the relevant guard layers intentionally.

## Recommended Production Setup

```python
app = QuickAPI(
    "Production API",
    secure=True,
    ml=True,
    ml_guard=True,
    max_body_size=1024 * 1024,
    auth_tokens={"replace-me"},
)
```

Use a reverse proxy such as nginx for TLS, compression, connection limits, and network-level filtering.

## Known Gaps

- Native route matching is a bridge, not yet the only routing source of truth.
- Benchmarks against FastAPI, Flask, Starlette, Go, and C# are still needed.
- ASGI lifecycle support is basic and should be expanded with more production tests.
- The built-in model should be evaluated with real datasets before being marketed as a security ML model.
- WebSocket security and streaming upload policy are not finalized.

## Reporting Security Issues

Do not publish exploit details publicly before maintainers have time to respond.

Open a private report or contact the project owner with:

- affected version or commit
- reproduction steps
- expected and actual behavior
- impact assessment
- suggested fix, if known
