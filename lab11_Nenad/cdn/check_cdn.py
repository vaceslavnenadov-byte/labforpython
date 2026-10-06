"""Сравнение загрузки ресурсов напрямую с origin и через CDN edge.

Перед запуском: python origin_server.py и python edge_server.py (в отдельных терминалах).
"""

import time

import requests

ORIGIN = "http://127.0.0.1:8080"
EDGE = "http://127.0.0.1:8081"
RESOURCES = ["images/seated.svg", "images/coupe.svg", "images/sv.svg",
             "css/style.v1.css", "css/style.v2.css", "js/app.js"]


def fetch(base: str, path: str) -> tuple[float, requests.Response]:
    start = time.perf_counter()
    response = requests.get(f"{base}/static/{path}", timeout=5)
    return (time.perf_counter() - start) * 1000, response


def main() -> None:
    requests.post(f"{EDGE}/purge", timeout=5)
    print(f"{'Ресурс':<20}{'Источник':<10}{'Запрос':<8}{'мс':>8}{'Байт':>7}  {'X-Cache':<8}{'Age':<5}Cache-Control")
    for path in RESOURCES:
        for name, base in (("origin", ORIGIN), ("CDN", EDGE)):
            for attempt in (1, 2):
                ms, r = fetch(base, path)
                print(f"{path:<20}{name:<10}{attempt:<8}{ms:>8.1f}{len(r.content):>7}  "
                      f"{r.headers.get('X-Cache', '-'):<8}{r.headers.get('Age', '-'):<5}"
                      f"{r.headers.get('Cache-Control')}")
    print("\nETag первого изображения:", requests.get(f"{ORIGIN}/static/images/sv.svg").headers.get("ETag"))
    etag = requests.get(f"{ORIGIN}/static/images/sv.svg").headers.get("ETag")
    conditional = requests.get(f"{ORIGIN}/static/images/sv.svg", headers={"If-None-Match": etag})
    print("Повторный запрос с If-None-Match:", conditional.status_code, "(304 = Not Modified)")


if __name__ == "__main__":
    main()
