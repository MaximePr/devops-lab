import os
from pathlib import Path

import psycopg

SCHEMA = Path(__file__).parent / "sql" / "001_init.sql"


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        conn.execute(SCHEMA.read_text())
    print("migration appliquée")


if __name__ == "__main__":
    main()
