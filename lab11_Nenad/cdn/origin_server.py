"""Origin-сервер статического контента (порт 8080).

Задаёт Cache-Control: изображения кэшируются на 1 час, версионированные CSS — на год,
JS — на 5 минут. Чтобы различие с CDN было заметно, имитируется удалённость origin (задержка 150 мс).
"""

import time
from pathlib import Path

from flask import Flask, send_from_directory

STATIC_DIR = Path(__file__).parent / "static"
ORIGIN_DELAY = 0.15

app = Flask(__name__, static_folder=None)  # отключаем встроенный /static


def cache_policy(path: str) -> str:
    if path.startswith("images/"):
        return "public, max-age=3600"
    if path.startswith("css/") and ".v" in path:
        return "public, max-age=31536000, immutable"
    if path.startswith("js/"):
        return "public, max-age=300"
    return "no-cache"


@app.get("/static/<path:path>")
def static_file(path):
    time.sleep(ORIGIN_DELAY)
    response = send_from_directory(STATIC_DIR, path, conditional=True, etag=True)
    response.headers["Cache-Control"] = cache_policy(path)
    response.headers["X-Served-By"] = "origin"
    return response


if __name__ == "__main__":
    app.run(port=8080)
