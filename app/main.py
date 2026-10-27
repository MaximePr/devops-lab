import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

# Seule configuration : l'adresse de la base. Absente = crash au démarrage, et c'est voulu.
DATABASE_URL = os.environ["DATABASE_URL"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pool neuf à chaque démarrage : un pool fermé ne peut jamais être rouvert.
    app.state.pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=False)
    # wait=False : l'app démarre même si la base est indisponible.
    app.state.pool.open(wait=False)
    yield
    app.state.pool.close()


app = FastAPI(title="events-api", lifespan=lifespan)


class Event(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    payload: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    # Liveness : le process répond. Ne dépend volontairement PAS de la base.
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response):
    # Readiness : l'app peut servir du trafic seulement si la base répond.
    try:
        with app.state.pool.connection(timeout=2) as conn:
            conn.execute("SELECT 1")
    except Exception:
        response.status_code = 503
        return {"status": "database unavailable"}
    return {"status": "ready"}


@app.post("/events", status_code=201)
def create_event(event: Event):
    with app.state.pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO events (type, payload) VALUES (%s, %s) RETURNING id",
            (event.type, Jsonb(event.payload)),
        ).fetchone()
    return {"id": row[0]}


@app.get("/events/stats")
def stats():
    with app.state.pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT type, date_trunc('hour', created_at) AS hour, count(*) AS total
            FROM events
            GROUP BY type, hour
            ORDER BY hour DESC, type
            """
        ).fetchall()
    return [{"type": t, "hour": h.isoformat(), "total": n} for t, h, n in rows]
