def build_openapi(app) -> dict:
    paths = {}
    for route in app.routes:
        item = paths.setdefault(route.path, {})
        item[route.method.lower()] = {
            "summary": route.name,
            "x-quickapi": {
                "ml_check": route.ml_check,
                "auth": route.auth,
                "rate_limit": route.rate_limit,
                "native": bool(route.native),
            },
            "responses": {
                "200": {"description": "Success"},
                **{str(code): {"description": "Declared error"} for code in route.errors},
            },
        }
    return {
        "openapi": "3.1.0",
        "info": {"title": app.config.name, "version": "0.1.0"},
        "paths": paths,
    }
