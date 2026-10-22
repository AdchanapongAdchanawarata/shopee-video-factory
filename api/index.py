import os
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Shopee Video Factory API (Vercel Serverless)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_DB_PATH = BASE_DIR / "data" / "products_db.json"

@app.get("/api/health")
def health():
    return {"status": "ok", "platform": "Vercel Serverless", "cost": "0 THB"}

@app.get("/api/products/top10")
def get_top10():
    """Return top 10 recommended winning products for Shopee Affiliate."""
    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                items = list(db.values())
                items.sort(key=lambda x: x.get("rank", 99))
                return items[:10]
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return []

@app.get("/api/product/{product_id}")
def get_product(product_id: str):
    """Return specific product data."""
    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                if product_id in db:
                    p = db[product_id]
                    return {
                        "exists": True,
                        "product_id": product_id,
                        "product_data": p,
                        "video_exists": False
                    }
        except Exception:
            pass
    return {"exists": False, "product_id": product_id}
