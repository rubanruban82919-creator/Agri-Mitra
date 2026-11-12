from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json
import mimetypes
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "agrimitra.db"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
FRONTEND_DIR = ROOT / "frontend"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AgriMitra API", version="0.8.0",
              description="Backend API for farm registration and drone media uploads.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            farmer_name TEXT NOT NULL,
            village TEXT, district TEXT, soil_type TEXT, water_source TEXT,
            crop TEXT, area_sq_m REAL NOT NULL, area_acres REAL NOT NULL,
            area_hectares REAL NOT NULL, boundary_json TEXT NOT NULL,
            notes TEXT, created_at TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS harvest_losses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop TEXT NOT NULL, area_acres REAL NOT NULL,
            expected_yield_kg REAL NOT NULL, actual_yield_kg REAL NOT NULL,
            loss_kg REAL NOT NULL, loss_percent REAL NOT NULL,
            price_per_kg REAL NOT NULL, estimated_value_inr REAL NOT NULL,
            method TEXT, harvest_date TEXT, created_at TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS produce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT NOT NULL, location TEXT NOT NULL, crop TEXT NOT NULL,
            quantity_kg REAL NOT NULL, price_per_kg REAL NOT NULL,
            quality TEXT, buyer_type TEXT, contact_phone TEXT NOT NULL,
            notes TEXT, created_at TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )""")

@app.on_event("startup")
def startup():
    init_db()

class BoundaryPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    farmer_name: str = Field(min_length=1, max_length=120)
    village: str = ""
    district: str = ""
    soil_type: str = ""
    water_source: str = ""
    crop: str = ""
    area_sq_m: float = Field(gt=0)
    area_acres: float = Field(gt=0)
    area_hectares: float = Field(gt=0)
    boundary: list[BoundaryPoint] = Field(min_length=3)
    notes: str = ""

def farm_dict(row):
    item = dict(row)
    item["boundary"] = json.loads(item.pop("boundary_json"))
    return item

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AgriMitra API", "version": app.version}

@app.post("/api/farms", status_code=201)
def create_farm(farm: FarmCreate):
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO farms
            (name, farmer_name, village, district, soil_type, water_source, crop,
             area_sq_m, area_acres, area_hectares, boundary_json, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (farm.name, farm.farmer_name, farm.village, farm.district,
              farm.soil_type, farm.water_source, farm.crop, farm.area_sq_m,
              farm.area_acres, farm.area_hectares,
              json.dumps([p.model_dump() for p in farm.boundary]),
              farm.notes, now))
        farm_id = cur.lastrowid
        row = conn.execute("SELECT * FROM farms WHERE id=?", (farm_id,)).fetchone()
    return farm_dict(row)

@app.get("/api/farms")
def list_farms():
    with db() as conn:
        rows = conn.execute("SELECT * FROM farms ORDER BY id DESC").fetchall()
    return [farm_dict(r) for r in rows]

@app.get("/api/farms/{farm_id}")
def get_farm(farm_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM farms WHERE id=?", (farm_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Farm not found")
    return farm_dict(row)

@app.delete("/api/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM farms WHERE id=?", (farm_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Farm not found")
    return None


class ProduceCreate(BaseModel):
    farmer_name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=160)
    crop: str = Field(min_length=1, max_length=100)
    quantity_kg: float = Field(gt=0)
    price_per_kg: float = Field(gt=0)
    quality: str = ""
    buyer_type: str = "Any buyer"
    contact_phone: str = Field(min_length=5, max_length=30)
    notes: str = Field(default="", max_length=1000)


class HarvestLossCreate(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    area_acres: float = Field(gt=0)
    expected_yield_kg: float = Field(gt=0)
    actual_yield_kg: float = Field(ge=0)
    loss_kg: float = Field(ge=0)
    loss_percent: float = Field(ge=0, le=100)
    price_per_kg: float = Field(ge=0)
    estimated_value_inr: float = Field(ge=0)
    method: str = ""
    harvest_date: str = ""

@app.post("/api/harvest-loss", status_code=201)
def create_harvest_loss(item: HarvestLossCreate):
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO harvest_losses
            (crop, area_acres, expected_yield_kg, actual_yield_kg, loss_kg,
             loss_percent, price_per_kg, estimated_value_inr, method, harvest_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.crop, item.area_acres, item.expected_yield_kg,
              item.actual_yield_kg, item.loss_kg, item.loss_percent,
              item.price_per_kg, item.estimated_value_inr, item.method,
              item.harvest_date, now))
        row = conn.execute("SELECT * FROM harvest_losses WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.get("/api/harvest-loss")
def list_harvest_losses():
    with db() as conn:
        rows = conn.execute("SELECT * FROM harvest_losses ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]

@app.post("/api/produce", status_code=201)
def create_produce_listing(item: ProduceCreate):
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO produce
            (farmer_name, location, crop, quantity_kg, price_per_kg, quality,
             buyer_type, contact_phone, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.farmer_name, item.location, item.crop, item.quantity_kg,
              item.price_per_kg, item.quality, item.buyer_type,
              item.contact_phone, item.notes, now))
        row = conn.execute("SELECT * FROM produce WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.get("/api/produce")
def list_produce_listings():
    with db() as conn:
        rows = conn.execute("SELECT * FROM produce ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]

@app.get("/api/produce/{listing_id}")
def get_produce_listing(listing_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM produce WHERE id=?", (listing_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Produce listing not found")
    return dict(row)

@app.post("/api/media/upload", status_code=201)
async def upload_media(file: UploadFile = File(...)):
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise HTTPException(400, "Only image and video files are allowed.")
    max_bytes = 250 * 1024 * 1024
    stored_name = f"{uuid.uuid4().hex}{Path(file.filename or 'media').suffix[:12]}"
    destination = UPLOAD_DIR / stored_name
    size = 0
    try:
        with destination.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    out.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(413, "File exceeds 250 MB limit.")
                out.write(chunk)
    finally:
        await file.close()
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO media (original_name, stored_name, content_type, size_bytes, created_at) VALUES (?, ?, ?, ?, ?)",
            (file.filename or stored_name, stored_name, content_type, size, now))
        media_id = cur.lastrowid
    return {"id": media_id, "original_name": file.filename or stored_name,
            "stored_name": stored_name, "content_type": content_type,
            "size_bytes": size, "created_at": now, "url": f"/uploads/{stored_name}"}

@app.get("/api/media")
def list_media():
    with db() as conn:
        rows = conn.execute("SELECT * FROM media ORDER BY id DESC").fetchall()
    return [{"id": r["id"], "original_name": r["original_name"],
             "content_type": r["content_type"], "size_bytes": r["size_bytes"],
             "created_at": r["created_at"], "url": f"/uploads/{r['stored_name']}"}
            for r in rows]

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

@app.get("/")
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")
