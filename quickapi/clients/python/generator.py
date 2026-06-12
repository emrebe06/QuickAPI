from quickapi.clients.generator import generate_client


def generate(app) -> str:
    return generate_client(app, "python")
