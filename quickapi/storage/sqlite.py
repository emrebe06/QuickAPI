import sqlite3


def connect(path: str = "quickapi.db"):
    return sqlite3.connect(path)
