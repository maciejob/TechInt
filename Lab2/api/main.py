from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/data/shop.db")

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
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      price REAL NOT NULL CHECK (price >= 0)
    );

    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      product_id INTEGER NOT NULL REFERENCES products(id),
      qty INTEGER NOT NULL CHECK (qty >= 1),
      price REAL NOT NULL CHECK (price >= 0)
    );

    -- pomocnicza tabela dla koszyka (1 globalny koszyk)
    CREATE TABLE IF NOT EXISTS cart_items (
      product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
      qty INTEGER NOT NULL CHECK (qty >= 1)
    );
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

# --------- Schemy ---------
class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)

class CartAddIn(BaseModel):
    product_id: int
    qty: int = Field(ge=1)

class CartPatchIn(BaseModel):
    product_id: int
    qty: int = Field(ge=1)

# --------- Produkty ---------
@app.get("/api/products")
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT id, name, price FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/products", status_code=201)
def add_product(p: ProductIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products(name, price) VALUES(?, ?)",
        (p.name.strip(), float(p.price)),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

# (Opcjonalne, ale pomaga w "CRUD"; UI tego nie musi używać)
@app.patch("/api/products/{product_id}")
def update_product(product_id: int, p: ProductIn):
    conn = get_db()
    exists = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="product not found")
    conn.execute(
        "UPDATE products SET name = ?, price = ? WHERE id = ?",
        (p.name.strip(), float(p.price), product_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    conn = get_db()
    cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="product not found")
    return Response(status_code=204)

# --------- Koszyk ---------
def cart_view(conn: sqlite3.Connection):
    rows = conn.execute("""
      SELECT
        ci.product_id,
        p.name,
        p.price,
        ci.qty,
        (p.price * ci.qty) AS line_total
      FROM cart_items ci
      JOIN products p ON p.id = ci.product_id
      ORDER BY ci.product_id
    """).fetchall()
    items = [dict(r) for r in rows]
    total = sum(i["line_total"] for i in items)
    return {"items": items, "total": total}

@app.get("/api/cart")
def get_cart():
    conn = get_db()
    data = cart_view(conn)
    conn.close()
    return data

@app.post("/api/cart/add")
def cart_add(req: CartAddIn):
    conn = get_db()
    p = conn.execute("SELECT id FROM products WHERE id = ?", (req.product_id,)).fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="product not found")

    existing = conn.execute("SELECT qty FROM cart_items WHERE product_id = ?", (req.product_id,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE cart_items SET qty = qty + ? WHERE product_id = ?",
            (req.qty, req.product_id),
        )
    else:
        conn.execute(
            "INSERT INTO cart_items(product_id, qty) VALUES(?, ?)",
            (req.product_id, req.qty),
        )
    conn.commit()
    data = cart_view(conn)
    conn.close()
    return data

@app.patch("/api/cart/item")
def cart_patch(req: CartPatchIn):
    conn = get_db()
    existing = conn.execute("SELECT qty FROM cart_items WHERE product_id = ?", (req.product_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="cart item not found")
    conn.execute("UPDATE cart_items SET qty = ? WHERE product_id = ?", (req.qty, req.product_id))
    conn.commit()
    data = cart_view(conn)
    conn.close()
    return data

@app.delete("/api/cart/item/{product_id}")
def cart_delete(product_id: int):
    conn = get_db()
    cur = conn.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="cart item not found")
    data = cart_view(conn)
    conn.close()
    return data

# --------- Checkout / Zamówienie ---------
@app.post("/api/checkout", status_code=201)
def checkout():
    conn = get_db()
    try:
        conn.execute("BEGIN;")

        cart = conn.execute("SELECT product_id, qty FROM cart_items ORDER BY product_id").fetchall()
        if not cart:
            raise HTTPException(status_code=409, detail="cart is empty")

        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute("INSERT INTO orders(created_at) VALUES(?)", (created_at,))
        order_id = cur.lastrowid

        total = 0.0
        for row in cart:
            product_id = row["product_id"]
            qty = row["qty"]

            p = conn.execute("SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()
            if not p:
                raise HTTPException(status_code=409, detail=f"product missing: {product_id}")

            price_snapshot = float(p["price"])  # snapshot ceny
            line_total = price_snapshot * qty
            total += line_total

            conn.execute("""
              INSERT INTO order_items(order_id, product_id, qty, price)
              VALUES(?, ?, ?, ?)
            """, (order_id, product_id, qty, price_snapshot))

        conn.execute("DELETE FROM cart_items")  # po checkout koszyk pusty
        conn.commit()
        return {"order_id": order_id, "total": total}

    except HTTPException:
        conn.execute("ROLLBACK;")
        raise
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.close()
