from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date, timedelta
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/library.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    CREATE TABLE IF NOT EXISTS members (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      copies INTEGER NOT NULL DEFAULT 1 CHECK (copies >= 0)
    );

    CREATE TABLE IF NOT EXISTS loans (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
      book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
      loan_date TEXT NOT NULL,
      due_date TEXT NOT NULL,
      return_date TEXT NULL
    );
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

class MemberIn(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)

class BookIn(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    copies: int = Field(default=1, ge=0)

class BorrowIn(BaseModel):
    member_id: int
    book_id: int
    days: int | None = Field(default=14, ge=1, le=365)

class ReturnIn(BaseModel):
    loan_id: int

@app.get("/api/members")
def list_members():
    conn = get_db()
    rows = conn.execute("SELECT id, name, email FROM members ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/members", status_code=201)
def add_member(m: MemberIn):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO members(name, email) VALUES(?, ?)",
            (m.name.strip(), m.email.strip().lower()),
        )
        conn.commit()
        new_id = cur.lastrowid
        return {"id": new_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="email already exists")
    finally:
        conn.close()

@app.get("/api/books")
def list_books():
    conn = get_db()
    rows = conn.execute("""
      SELECT
        b.id, b.title, b.author, b.copies,
        (b.copies - COALESCE(al.active_loans, 0)) AS available
      FROM books b
      LEFT JOIN (
        SELECT book_id, COUNT(*) AS active_loans
        FROM loans
        WHERE return_date IS NULL
        GROUP BY book_id
      ) al ON al.book_id = b.id
      ORDER BY b.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/books", status_code=201)
def add_book(b: BookIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO books(title, author, copies) VALUES(?, ?, ?)",
        (b.title.strip(), b.author.strip(), b.copies),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

@app.get("/api/loans")
def list_loans():
    conn = get_db()
    rows = conn.execute("""
      SELECT
        l.id,
        l.loan_date, l.due_date, l.return_date,
        m.id AS member_id, m.name AS member_name, m.email AS member_email,
        b.id AS book_id, b.title AS book_title, b.author AS book_author
      FROM loans l
      JOIN members m ON m.id = l.member_id
      JOIN books b ON b.id = l.book_id
      ORDER BY l.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/loans/borrow", status_code=201)
def borrow(req: BorrowIn):
    conn = get_db()

    # sprawdź czy member i book istnieją
    m = conn.execute("SELECT id FROM members WHERE id = ?", (req.member_id,)).fetchone()
    if not m:
        conn.close()
        raise HTTPException(status_code=404, detail="member not found")
    b = conn.execute("SELECT id, copies FROM books WHERE id = ?", (req.book_id,)).fetchone()
    if not b:
        conn.close()
        raise HTTPException(status_code=404, detail="book not found")

    active = conn.execute(
        "SELECT COUNT(*) AS c FROM loans WHERE book_id = ? AND return_date IS NULL",
        (req.book_id,),
    ).fetchone()["c"]

    if active >= b["copies"]:
        conn.close()
        raise HTTPException(status_code=409, detail="no copies available")

    loan_dt = date.today()
    due_dt = loan_dt + timedelta(days=req.days or 14)

    cur = conn.execute("""
      INSERT INTO loans(member_id, book_id, loan_date, due_date, return_date)
      VALUES(?, ?, ?, ?, NULL)
    """, (req.member_id, req.book_id, loan_dt.isoformat(), due_dt.isoformat()))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

@app.post("/api/loans/return")
def return_loan(req: ReturnIn):
    conn = get_db()
    row = conn.execute("SELECT id, return_date FROM loans WHERE id = ?", (req.loan_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="loan not found")

    if row["return_date"] is not None:
        conn.close()
        raise HTTPException(status_code=409, detail="already returned")

    conn.execute(
        "UPDATE loans SET return_date = ? WHERE id = ?",
        (date.today().isoformat(), req.loan_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
