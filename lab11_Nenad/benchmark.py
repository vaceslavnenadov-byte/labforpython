"""Сравнение времени повторного чтения расписания: SQLite (JOIN) vs Redis (GET).

Требуется запущенный Redis (REDIS_URL, по умолчанию redis://localhost:6379/0).
Если установлен matplotlib — строится график benchmark.png.
"""

import json
import time

from cache import create_cache, NullCache
from database import connect, init_db
from repository import TrainRepository


def main() -> None:
    db = connect(":memory:")
    init_db(db)
    repo = TrainRepository(db)
    cache = create_cache()
    if isinstance(cache, NullCache):
        print("Redis недоступен — benchmark невозможен.")
        return
    cache.set_json("bench:schedule:2", repo.schedule(2), ttl=600)

    rows = []
    for n in (100, 1000, 10000):
        start = time.perf_counter()
        for _ in range(n):
            repo.schedule(2)
        sql = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(n):
            json.loads(cache.client.get("bench:schedule:2"))
        redis_time = time.perf_counter() - start
        rows.append((n, sql, redis_time))

    print(f"{'Запросов':>9} | {'SQLite, с':>10} | {'Redis, с':>10} | {'SQLite, мкс/запр':>16} | {'Redis, мкс/запр':>15}")
    for n, sql, rd in rows:
        print(f"{n:>9} | {sql:>10.4f} | {rd:>10.4f} | {sql / n * 1e6:>16.1f} | {rd / n * 1e6:>15.1f}")
    cache.delete("bench:schedule:2")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен — график не построен.")
        return
    plt.plot([r[0] for r in rows], [r[1] for r in rows], marker="o", label="SQLite (JOIN)")
    plt.plot([r[0] for r in rows], [r[2] for r in rows], marker="o", label="Redis (GET)")
    plt.xscale("log")
    plt.xlabel("Количество запросов")
    plt.ylabel("Общее время, с")
    plt.title("Повторное чтение расписания поезда")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("benchmark.png", dpi=120, bbox_inches="tight")
    print("График сохранён: benchmark.png")


if __name__ == "__main__":
    main()
