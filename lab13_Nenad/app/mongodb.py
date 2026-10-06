"""Подключение к MongoDB. Без сервера можно работать на mongomock (флаг --mock)."""

import os


def get_database(use_mock: bool = False, name: str = "railway"):
    if use_mock:
        import mongomock
        return mongomock.MongoClient().get_database(name)
    from pymongo import MongoClient
    url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = MongoClient(url, serverSelectionTimeoutMS=2000)
    client.admin.command("ping")          # проверяем доступность сразу
    return client.get_database(name)
