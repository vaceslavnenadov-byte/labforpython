"""Локальная имитация CDN edge-сервера (порт 8081).

Получает файл с origin при первом запросе (X-Cache: MISS), сохраняет его на время max-age
из Cache-Control и отдаёт последующие запросы из своего кэша (X-Cache: HIT) с заголовком Age.
"""

import os
import re
import time

import requests
from flask import Flask, Response

ORIGIN = os.getenv("ORIGIN_URL", "http://127.0.0.1:8080")
app = Flask(__name__, static_folder=None)  # отключаем встроенный /static
storage: dict[str, dict] = {}   # path -> {body, headers, stored_at, max_age}


def max_age(cache_control: str) -> int:
    if "no-cache" in cache_control or "private" in cache_control:
        return 0
    match = re.search(r"max-age=(\d+)", cache_control)
    return int(match.group(1)) if match else 0


@app.get("/static/<path:path>")
def edge(path):
    entry = storage.get(path)
    if entry and time.time() - entry["stored_at"] < entry["max_age"]:
        headers = dict(entry["headers"])
        headers["Age"] = str(int(time.time() - entry["stored_at"]))
        headers["X-Cache"] = "HIT"
        return Response(entry["body"], status=200, headers=headers)

    upstream = requests.get(f"{ORIGIN}/static/{path}", timeout=5)
    keep = {k: v for k, v in upstream.headers.items()
            if k in ("Content-Type", "Cache-Control", "ETag", "Last-Modified")}
    keep["X-Served-By"] = "edge-1"
    ttl = max_age(upstream.headers.get("Cache-Control", ""))
    if upstream.status_code == 200 and ttl > 0:
        storage[path] = {"body": upstream.content, "headers": keep, "stored_at": time.time(), "max_age": ttl}
    keep["X-Cache"] = "MISS"
    keep["Age"] = "0"
    return Response(upstream.content, status=upstream.status_code, headers=keep)


@app.post("/purge")
def purge():
    """Сброс кэша edge (аналог purge в настоящих CDN)."""
    count = len(storage)
    storage.clear()
    return {"purged": count}


if __name__ == "__main__":
    app.run(port=8081)
