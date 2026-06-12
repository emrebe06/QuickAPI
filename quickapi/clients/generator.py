def generate_client(app, language: str = "python") -> str:
    routes = "\n".join(f"# {route.method} {route.path}" for route in app.routes)
    return f"# QuickAPI {language} client\n{routes}\n"
