"""Выполняет все запросы из sql/queries.sql на копии БД в памяти и печатает результаты."""

from pathlib import Path

from database import connect, init_db


def main() -> None:
    connection = connect(":memory:")
    init_db(connection)
    text = (Path(__file__).parent / "sql" / "queries.sql").read_text(encoding="utf-8")
    for block in text.split(";"):
        lines = [l for l in block.strip().splitlines()]
        if not lines:
            continue
        title = lines[0] if lines[0].startswith("--") else ""
        sql = "\n".join(l for l in lines if not l.startswith("--")).strip()
        if not sql:
            continue
        print(f"\n{title}")
        cursor = connection.execute(sql)
        if cursor.description:
            headers = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            print(" | ".join(headers))
            for row in rows:
                print(" | ".join(str(v) for v in row))
        else:
            print(f"Изменено строк: {cursor.rowcount}")
    connection.commit()


if __name__ == "__main__":
    main()
