def schema_from_example(example: dict) -> dict:
    return {key: type(value).__name__ for key, value in (example or {}).items()}
