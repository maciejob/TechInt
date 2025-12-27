from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/kanban.db")

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
    CREATE TABLE IF NOT EXISTS columns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      ord INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      col_id INTEGER NOT NULL REFERENCES columns(id),
      ord INTEGER NOT NULL
    );
    """)

    # Predefiniowane kolumny
    existing = conn.execute("SELECT COUNT(*) AS c FROM columns").fetchone()["c"]
    if existing == 0:
        conn.executemany(
            "INSERT INTO columns(name, ord) VALUES(?,?)",
            [("Todo", 1), ("Doing", 2), ("Done", 3)],
        )

    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

# --------- Schemy ---------
class TaskIn(BaseModel):
    title: str = Field(min_length=1)
    col_id: int

class TaskMoveIn(BaseModel):
    col_id: int
    ord: int = Field(ge=1)

# --------- Board ---------
@app.get("/api/board")
def get_board():
    conn = get_db()
    cols = conn.execute(
        "SELECT id, name, ord FROM columns ORDER BY ord"
    ).fetchall()
    tasks = conn.execute(
        "SELECT id, title, col_id, ord FROM tasks ORDER BY col_id, ord"
    ).fetchall()
    conn.close()
    return {
        "cols": [dict(c) for c in cols],
        "tasks": [dict(t) for t in tasks],
    }

# --------- Tasks ---------
@app.post("/api/tasks", status_code=201)
def add_task(t: TaskIn):
    conn = get_db()

    col = conn.execute(
        "SELECT id FROM columns WHERE id = ?", (t.col_id,)
    ).fetchone()
    if not col:
        conn.close()
        raise HTTPException(status_code=404, detail="column not found")

    max_ord = conn.execute(
        "SELECT COALESCE(MAX(ord), 0) AS m FROM tasks WHERE col_id = ?",
        (t.col_id,),
    ).fetchone()["m"]

    conn.execute(
        "INSERT INTO tasks(title, col_id, ord) VALUES(?,?,?)",
        (t.title.strip(), t.col_id, max_ord + 1),
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/api/tasks/{task_id}/move")
def move_task(task_id: int, m: TaskMoveIn):
    conn = get_db()

    task = conn.execute(
        "SELECT id FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="task not found")

    col = conn.execute(
        "SELECT id FROM columns WHERE id = ?", (m.col_id,)
    ).fetchone()
    if not col:
        conn.close()
        raise HTTPException(status_code=404, detail="column not found")

    # przesuwamy inne zadania w docelowej kolumnie
    conn.execute("""
      UPDATE tasks
      SET ord = ord + 1
      WHERE col_id = ? AND ord >= ?
    """, (m.col_id, m.ord))

    conn.execute("""
      UPDATE tasks
      SET col_id = ?, ord = ?
      WHERE id = ?
    """, (m.col_id, m.ord, task_id))

    conn.commit()
    conn.close()
    return {"ok": True}
