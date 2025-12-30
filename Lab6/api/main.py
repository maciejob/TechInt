from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/notes.db")

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
    CREATE TABLE IF NOT EXISTS notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS note_tags (
      note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
      tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
      PRIMARY KEY (note_id, tag_id)
    );
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

# --------- Schemy ---------
class NoteIn(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)

class TagsIn(BaseModel):
    tags: list[str]

# --------- Notes ---------
@app.get("/api/notes")
def list_notes(q: str | None = None):
    conn = get_db()
    if q:
        like = f"%{q}%"
        rows = conn.execute("""
          SELECT id, title, body, created_at
          FROM notes
          WHERE title LIKE ? OR body LIKE ?
          ORDER BY id DESC
        """, (like, like)).fetchall()
    else:
        rows = conn.execute("""
          SELECT id, title, body, created_at
          FROM notes
          ORDER BY id DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/notes", status_code=201)
def add_note(n: NoteIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO notes(title, body, created_at) VALUES(?,?,?)",
        (n.title.strip(), n.body.strip(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

# --------- Tags ---------
@app.get("/api/tags")
def list_tags():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name FROM tags ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/notes/{note_id}/tags")
def set_tags(note_id: int, t: TagsIn):
    conn = get_db()

    note = conn.execute(
        "SELECT id FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if not note:
        conn.close()
        raise HTTPException(status_code=404, detail="note not found")

    for name in t.tags:
        name = name.strip().lower()
        if not name:
            continue

        row = conn.execute(
            "SELECT id FROM tags WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            cur = conn.execute(
                "INSERT INTO tags(name) VALUES(?)", (name,)
            )
            tag_id = cur.lastrowid
        else:
            tag_id = row["id"]

        conn.execute(
            "INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES(?,?)",
            (note_id, tag_id),
        )

    conn.commit()
    conn.close()
    return {"ok": True}
