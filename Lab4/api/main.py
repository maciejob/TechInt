from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/movies.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS movies (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      year INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ratings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
      score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5)
    );
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

class MovieIn(BaseModel):
    title: str = Field(min_length=1)
    year: int = Field(ge=1800, le=3000)

class RatingIn(BaseModel):
    movie_id: int
    score: int = Field(ge=1, le=5)

@app.get("/api/movies")
def list_movies():
    conn = get_db()
    rows = conn.execute("""
      SELECT
        m.id,
        m.title,
        m.year,
        ROUND(COALESCE(AVG(r.score), 0), 2) AS avg_score,
        COUNT(r.id) AS votes
      FROM movies m
      LEFT JOIN ratings r ON r.movie_id = m.id
      GROUP BY m.id
      ORDER BY avg_score DESC, votes DESC, m.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/movies", status_code=201)
def add_movie(m: MovieIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO movies(title, year) VALUES(?, ?)",
        (m.title.strip(), m.year),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

@app.post("/api/ratings", status_code=201)
def add_rating(r: RatingIn):
    conn = get_db()
    movie = conn.execute("SELECT id FROM movies WHERE id = ?", (r.movie_id,)).fetchone()
    if not movie:
        conn.close()
        raise HTTPException(status_code=404, detail="movie not found")

    conn.execute(
        "INSERT INTO ratings(movie_id, score) VALUES(?, ?)",
        (r.movie_id, r.score),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
