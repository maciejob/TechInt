from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/blog.db")

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
    CREATE TABLE IF NOT EXISTS posts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS comments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
      author TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TEXT NOT NULL,
      approved INTEGER NOT NULL DEFAULT 0
    );
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

# --------- Schemy ---------
class PostIn(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)

class CommentIn(BaseModel):
    author: str = Field(min_length=1)
    body: str = Field(min_length=1)

# --------- Posty ---------
@app.get("/api/posts")
def list_posts():
    conn = get_db()
    rows = conn.execute("""
      SELECT id, title, body, created_at
      FROM posts
      ORDER BY id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/posts", status_code=201)
def add_post(p: PostIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO posts(title, body, created_at) VALUES(?,?,?)",
        (p.title.strip(), p.body.strip(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

# --------- Komentarze ---------
@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):
    conn = get_db()
    post = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="post not found")

    rows = conn.execute("""
      SELECT id, author, body, created_at
      FROM comments
      WHERE post_id = ? AND approved = 1
      ORDER BY id ASC
    """, (post_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/posts/{post_id}/comments", status_code=201)
def add_comment(post_id: int, c: CommentIn):
    conn = get_db()
    post = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(status_code=404, detail="post not found")

    cur = conn.execute("""
      INSERT INTO comments(post_id, author, body, created_at, approved)
      VALUES(?,?,?,?,0)
    """, (
        post_id,
        c.author.strip(),
        c.body.strip(),
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "approved": 0}

# --------- Moderacja ---------
@app.get("/api/moderation/pending")
def pending_comments():
    conn = get_db()
    rows = conn.execute("""
      SELECT id, post_id, author, body, created_at
      FROM comments
      WHERE approved = 0
      ORDER BY id ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/comments/{comment_id}/approve")
def approve_comment(comment_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT id, approved FROM comments WHERE id = ?",
        (comment_id,),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="comment not found")
    if row["approved"] == 1:
        conn.close()
        raise HTTPException(status_code=409, detail="already approved")

    conn.execute(
        "UPDATE comments SET approved = 1 WHERE id = ?",
        (comment_id,),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
