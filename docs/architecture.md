QuickAPI architecture
=====================

QuickAPI is split into three layers:

1. Python intelligence layer
   - Developer API: `QuickAPI`, decorators, `q` response factory.
   - Routing metadata, ML decisions, ecommerce presets, docs and CLI.
   - This is the layer users touch when they want to ship a backend quickly.

2. Listener layer
   - `quickapi.server.QuickListener` owns HTTP parsing, proxy headers, CORS,
     access logs and response writing.
   - `app.run()` is a convenience wrapper around the listener.
   - It is suitable behind nginx with `X-Forwarded-For` and `X-Real-IP`.

3. Native core layer
   - `quickapi/native` exposes a C ABI for future hot paths:
     JSON response formatting, route matching, status names, basic security
     checks, timing and native symbol loading.
   - Python remains the orchestration layer while C/C++ can take over speed
     sensitive paths without changing the user-facing API.

Nginx proxy shape
-----------------

QuickAPI should normally bind to localhost:

```bash
quickapi run examples.basic_api.main:app --host 127.0.0.1 --port 8080
```

Nginx can proxy to it:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
