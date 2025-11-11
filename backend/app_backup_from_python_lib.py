from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json

app = FastAPI(title="Backend for Telegram Sales Bot")
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

BASE = os.path.dirname(__file__) or '.'
FILES_DIR = os.path.join(BASE, "..", "fichiers")
DB_FILE = os.path.join(BASE, "..", "db", "sales_db.json")

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"sales": [], "leads": [], "sold_lines": {}}, f, indent=2, ensure_ascii=False)

def read_db():
    # ⚡ utilise utf-8-sig pour ignorer le BOM si présent
    with open(DB_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def write_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def list_products():
    pth = os.path.join(BASE, "..", "fichiers")
    prods = []
    for fname in sorted(os.listdir(pth)):
        prods.append(fname)
    return prods

class AddLead(BaseModel):
    name: str
    contact: str
    note: str = ""

class CheckoutRequest(BaseModel):
    user_id: int
    items: list

@app.get("/products")
def products():
    prods = list_products()
    db = read_db()
    sold = db.get("sold_lines", {})
    result = []
    for p in prods:
        path = os.path.join(FILES_DIR, p)
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        sold_count = len(sold.get(p, []))
        result.append({"filename": p, "total": len(lines), "sold": sold_count, "available": len(lines)-sold_count})
    return {"products": result}

@app.get("/next_line/{product}")
def next_line(product: str):
    db = read_db()
    sold = db.setdefault("sold_lines", {})
    if product not in sold:
        sold[product] = []
    path = os.path.join(FILES_DIR, product)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Product not found")
    with open(path, "r", encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    for i, line in enumerate(lines):
        if i not in sold[product]:
            sold[product].append(i)
            db["sales"].append({"product": product, "line_index": i, "line": line, "user_id": None})
            write_db(db)
            return {"line": line, "index": i}
    return {"line": None, "message": "Sold out"}

@app.post("/register_sale")
def register_sale(payload: dict):
    db = read_db()
    db.setdefault("sales", []).append(payload)
    write_db(db)
    return {"status": "ok"}

@app.post("/leads")
def add_lead(lead: AddLead):
    db = read_db()
    db.setdefault("leads", []).append({"name": lead.name, "contact": lead.contact, "note": lead.note})
    write_db(db)
    return {"status": "ok"}

@app.get("/sales")
def get_sales():
    db = read_db()
    return {"sales": db.get("sales", [])}
