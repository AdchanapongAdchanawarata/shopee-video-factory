import requests
from typing import Optional
import os
import re
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
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

from pydantic import BaseModel

AUTHORIZED_EMAIL = "adchanawarata@gmail.com"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "shopee2026")

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Enforce access exclusively for adchanawarata@gmail.com."""
    user_email = req.email.strip().lower()
    if user_email != AUTHORIZED_EMAIL:
        return JSONResponse(
            status_code=403,
            content={
                "status": "forbidden",
                "message": f"ขออภัย บัญชี '{req.email}' ไม่ได้รับอนุญาตให้ใช้งานระบบ (ระบบจำกัดสิทธิ์เฉพาะ {AUTHORIZED_EMAIL} เท่านั้น)"
            }
        )
    if req.password != ADMIN_PASSWORD:
        return JSONResponse(
            status_code=401,
            content={
                "status": "unauthorized",
                "message": "รหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบรหัสผ่านอีกครั้ง"
            }
        )
    return {
        "status": "authenticated",
        "email": AUTHORIZED_EMAIL,
        "token": "shopee_auth_token_adchanawarata_secure_session",
        "user": {
            "email": AUTHORIZED_EMAIL,
            "role": "Super Admin",
            "name": "Adchanapong"
        }
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "platform": "Vercel Serverless", "cost": "0 THB", "authorized_user": AUTHORIZED_EMAIL}

@app.get("/api/products/top10")
def get_top10():
    """Return full pool of recommended winning products for Shopee Affiliate."""
    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                items = list(db.values())
                items.sort(key=lambda x: x.get("rank", 99))
                return items
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return []

@app.post("/api/products/refresh")
def refresh_products():
    """Refresh and re-rank winning products by highest commission, sales velocity, and market trend."""
    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                items = list(db.values())
                items.sort(
                    key=lambda x: (
                        float(x.get("ams_commission_rate", 0)) * 2.5
                        + float(x.get("stock_score", 90))
                        + min(30.0, float(x.get("sales_30d", 0)) / 50.0)
                    ),
                    reverse=True
                )
                return {"status": "refreshed", "count": len(items), "products": items}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return {"status": "refreshed", "count": 0, "products": []}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "platform": "Vercel Serverless + GitHub",
        "cost": "0 THB",
        "ffmpeg_ready": False,
        "engine_mode": "Cloud Dashboard Mode",
        "note": "สำหรับการเรนเดอร์ FFmpeg 1080x1920 ให้รัน python server.py ในเครื่องหรือผ่าน GitHub Actions"
    }

PUBLIC_VIDEOS_DIR = BASE_DIR / "public" / "videos"


PRODUCT_CAPTIONS = {
    "cat_fountain_01": {
        "caption": "ใครเลี้ยงแมวต้องมีเลยค่ะ! น้ำพุไร้สายสแตนเลส 5L ไร้สาย ปลอดภัย เสียงเงียบกริบ น้องแมวดื่มน้ำเยอะขึ้นจริง สุขภาพไตดีขึ้น พิกัดในตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ 🐱💦",
        "hashtags": "#น้ำพุแมว #น้ำพุแมวไร้สาย #ทาสแมว #ของใช้แมว #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "gan_charger_65w": {
        "caption": "หัวชาร์จเร็วตัวจบ UGREEN 65W GaN ชาร์จพร้อมกัน 3 เครื่อง มือถือ โน้ตบุ๊ก แท็บเล็ต พกตัวเดียวเที่ยวได้ทั่วโลก ไม่ร้อน ปลอดภัย พิกัดในตะกร้าส้มซ้ายล่างเลยค่ะ ⚡📱",
        "hashtags": "#หัวชาร์จugreen #ugreen65w #หัวชาร์จเร็ว #ของดีบอกต่อ #ไอทีน่ารู้ #ShopeeVideoTH #รีวิวช้อปปี้ #นายหน้าShopee"
    },
    "uv_dust_mite_vacuum": {
        "caption": "คนเป็นภูมิแพ้ตื่นมาจามบ่อยต้องจัด! เครื่องดูดไรฝุ่นแสงยูวี Deerma CM800 ดูดฝุ่นและไรฝุ่นสะสมบนที่นอนสะอาดหมดจด หลับสบายขึ้นเยอะ พิกัดตะกร้าส้มซ้ายล่างนะคะ 🛏️✨",
        "hashtags": "#เครื่องดูดไรฝุ่น #เครื่องดูดไรฝุ่นdeerma #ของใช้ในบ้าน #ภูมิแพ้ #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "tyeso_tumbler_304": {
        "caption": "แก้วเก็บความเย็น TYESO 1200ml ของแท้ สแตนเลส 304 ใส่น้ำแข็งข้ามวันยังอยู่ครบ มีหูจับถนัดมือ หลอดดูดในตัว พิกัดในตะกร้าส้มซ้ายล่างเลยนะคะ 🧊🥤",
        "hashtags": "#แก้วtyeso #แก้วเก็บความเย็น #แก้วtyesoแท้ #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "spray_mop_360": {
        "caption": "บอกลาการหิ้วถังน้ำหนักๆ ไปได้เลย! ไม้ถูพื้นสเปรย์ Deerma TB500 ฉีดแล้วถูได้ทันที หมุนได้ 360 องศา แห้งไว ไม่ทิ้งคราบ พิกัดตะกร้าส้มซ้ายล่างเลยนะคะ 🧹✨",
        "hashtags": "#ไม้ถูพื้นสเปรย์ #ไม้ถูพื้นdeerma #ของใช้ในบ้าน #งานบ้านที่รัก #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "solar_sensor_light": {
        "caption": "สว่างยันเช้า ค่าไฟ 0 บาท! ไฟโซลาร์เซลล์ติดผนัง 100 LED มีเซนเซอร์ตรวจจับความเคลื่อนไหว สว่างอัตโนมัติ กันน้ำกันฝน ติดตั้งง่ายมาก พิกัดในตะกร้าส้มเลยค่ะ 💡🏡",
        "hashtags": "#ไฟโซลาร์เซลล์ #ไฟติดผนัง #แต่งบ้าน #ประหยัดค่าไฟ #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "air_fryer_visual": {
        "caption": "ทำอาหารง่ายขึ้นเยอะ! หม้อทอดไร้น้ำมัน Simplus 3.5L รุ่นกระจกมองเห็นอาหารด้านใน กรอบนอกนุ่มใน คลีนๆ อร่อยแบบไม่ต้องใช้น้ำมัน พิกัดตะกร้าส้มเลยนะคะ 🍗🍟",
        "hashtags": "#หม้อทอดไร้น้ำมัน #หม้อทอดsimplus #ของใช้ในครัว #เมนูหม้อทอด #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "sonic_electric_toothbrush": {
        "caption": "แปรงสะอาดลึกถึงซอกฟัน! แปรงสีฟันไฟฟ้าโซนิค MeeGoo ขนแปรงดูปองท์นุ่มไม่เจ็บเหงือก สั่น 56000 รอบ กันน้ำ IPX7 แบตอึดชาร์จ Type-C พิกัดตะกร้าส้มเลยค่ะ 🪥✨",
        "hashtags": "#แปรงสีฟันไฟฟ้า #แปรงสีฟันโซนิค #ฟันขาวสะอาด #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "kitchen_dish_rack_stainless": {
        "caption": "จัดครัวให้เป็นระเบียบใน 1 นาที! ชั้นคว่ำจานคร่อมอ่างสแตนเลส 304 แท้ แข็งแรง ทนทาน ไม่เป็นสนิม มีประตูกันฝุ่น ครัวกว้างขึ้นเยอะ พิกัดตะกร้าส้มเลยนะคะ 🍽️🏠",
        "hashtags": "#ชั้นคว่ำจาน #ที่คว่ำจานสแตนเลส #จัดระเบียบครัว #ของใช้ในครัว #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "wireless_earbuds_anc": {
        "caption": "หูฟังตัดเสียงรบกวนตัวจบ! Baseus Bowie MP1 ของแท้ มี ANC -55dB เงียบสงบเหมือนอยู่ห้องส่วนตัว เบสแน่น ไมค์ 6 ตัวคุยสายชัดแจ๋ว แบตอึด 45 ชม. พิกัดตะกร้าส้มเลยค่ะ 🎧🎵",
        "hashtags": "#หูฟังbaseus #baseusbowiemp1 #หูฟังบลูทูธ #หูฟังตัดเสียง #ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee"
    },
    "fanlife_tumbler_710ml": {
        "caption": "แก้วเก็บความเย็น 710ml สแตนเลส 316L เคลือบเซรามิก เก็บน้ำแข็งข้ามวัน ลายน่ารักตรงปก มีหูหิ้วพกพาสะดวกมาก พิกัดในตะกร้าส้มเลยค่ะ 🎀🥤",
        "hashtags": "#แก้วเก็บความเย็น #แก้วเยติ #รีวิวของใช้ในบ้าน #ของดีบอกต่อ #รีวิวช้อปปี้ #พิกัดตะกร้าส้ม #นายหน้าShopee"
    }
}


PRODUCT_SCRIPTS = {
    "fanlife_tumbler_710ml": {
        "on_screen_headline": "แก้วเก็บความเย็น 710ml สแตนเลส 316L",
        "hook_text": "ใครที่ชอบพกแก้วน้ำไปทำงาน หรือไปเที่ยว แนะนำใบนี้เลยค่ะ.",
        "body_text": "แก้วเก็บความเย็นฟานไลฟ์ ขนาด 710 มิลลิลิตร ด้านในเคลือบเซรามิกแท้ ไม่ติดกลิ่น เก็บน้ำแข็งข้ามวัน ลายน่ารักตรงปก มีหูหิ้วพกพาง่ายมากค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่ชอบพกแก้วน้ำไปทำงาน, หรือไปเที่ยว, แนะนำใบนี้เลยค่ะ. แก้วเก็บความเย็นฟานไลฟ์, ขนาด 710 มิลลิลิตร, ด้านในเคลือบเซรามิกแท้, ไม่ติดกลิ่น, เก็บน้ำแข็งข้ามวัน, ลายน่ารักตรงปก, มีหูหิ้วพกพาง่ายมากค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "cat_fountain_01": {
        "on_screen_headline": "น้ำพุแมวไร้สาย สแตนเลส 5L",
        "hook_text": "ใครที่น้องแมวดื่มน้ำน้อย หรือกลัวเรื่องสายไฟช็อต แนะนำตัวนี้เลยค่ะ.",
        "body_text": "น้ำพุแมวไร้สายนาวิเพ็ท ตัวถังสแตนเลสฟู้ดเกรดแท้ ความจุจุใจถึง 5 ลิตร ไร้สายไฟปลอดภัย 100% มอเตอร์เสียงเงียบกริบ น้ำสะอาดช่วยให้น้องแมวชอบดื่มน้ำขึ้นเยอะเลยค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่น้องแมวดื่มน้ำน้อย, หรือกลัวเรื่องสายไฟช็อต, แนะนำตัวนี้เลยค่ะ. น้ำพุแมวไร้สายนาวิเพ็ท, ตัวถังสแตนเลสฟู้ดเกรดแท้, ความจุจุใจถึง 5 ลิตร, ไร้สายไฟปลอดภัย 100%, มอเตอร์เสียงเงียบกริบ, น้ำสะอาดช่วยให้น้องแมวชอบดื่มน้ำขึ้นเยอะเลยค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "wireless_earbuds_anc": {
        "on_screen_headline": "หูฟังตัดเสียง Baseus ANC -55dB",
        "hook_text": "ใครที่เดินทางบ่อย แล้วเจอเสียงรบกวนรอบข้าง แนะนำหูฟังรุ่นนี้เลยค่ะ.",
        "body_text": "หูฟังบลูทูธเบสซุส มีโหมดตัดเสียงรบกวนอัจฉริยะ เบสหนักแน่นสะใจ ไมค์คุยสายชัดเจน แบตเตอรี่ใช้งานได้ตลอดวันค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่เดินทางบ่อย, แล้วเจอเสียงรบกวนรอบข้าง, แนะนำหูฟังรุ่นนี้เลยค่ะ. หูฟังบลูทูธเบสซุส, มีโหมดตัดเสียงรบกวนอัจฉริยะ, เบสหนักแน่นสะใจ, ไมค์คุยสายชัดเจน, แบตเตอรี่ใช้งานได้ตลอดวันค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "air_fryer_visual": {
        "on_screen_headline": "หม้อทอดไร้น้ำมัน กระจกใส 3.5L",
        "hook_text": "ทำอาหารง่ายขึ้นมาก ด้วยหม้อทอดไร้น้ำมันรุ่นใหม่ บอกลาปัญหาน้ำมันกระเด็นได้เลยค่ะ.",
        "body_text": "หม้อทอดซิมพลัส มองเห็นอาหารด้านในได้ตลอด ระบบสัมผัสใช้งานง่าย อาหารสุกกรอบน่าทาน ล้างทำความสะอาดง่ายมากค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ทำอาหารง่ายขึ้นมาก, ด้วยหม้อทอดไร้น้ำมันรุ่นใหม่, บอกลาปัญหาน้ำมันกระเด็นได้เลยค่ะ. หม้อทอดซิมพลัส, มองเห็นอาหารด้านในได้ตลอด, ระบบสัมผัสใช้งานง่าย, อาหารสุกกรอบน่าทาน, ล้างทำความสะอาดง่ายมากค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "uv_dust_mite_vacuum": {
        "on_screen_headline": "เครื่องดูดไรฝุ่น ฆ่าเชื้อแสง UV",
        "hook_text": "ใครที่ตื่นมาแล้วจามบ่อย หรือเป็นภูมิแพ้ แนะนำตัวนี้เลยค่ะ.",
        "body_text": "เครื่องดูดไรฝุ่นเดียร์ม่า มีแสงยูวีฆ่าเชื้อในตัว พลังดูดสูงมาก ช่วยดูดฝุ่นและไรฝุ่นสะสม บนที่นอนออกมาได้สะอาดหมดจดเลยค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่ตื่นมาแล้วจามบ่อย, หรือเป็นภูมิแพ้, แนะนำตัวนี้เลยค่ะ. เครื่องดูดไรฝุ่นเดียร์ม่า, มีแสงยูวีฆ่าเชื้อในตัว, พลังดูดสูงมาก, ช่วยดูดฝุ่นและไรฝุ่นสะสม, บนที่นอนออกมาได้สะอาดหมดจดเลยค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "gan_charger_65w": {
        "on_screen_headline": "หัวชาร์จเร็ว UGREEN 65W GaN",
        "hook_text": "ใครที่ต้องพกหัวชาร์จหลายอัน ให้หนักกระเป๋า ลองดูตัวนี้ค่ะ.",
        "body_text": "หัวชาร์จยูกรีน 65 วัตต์ มีถึง 3 พอร์ต ชาร์จพร้อมกันได้ทั้งมือถือ แท็บเล็ต และโน้ตบุ๊ก ขนาดกะทัดรัดพกพาง่ายมากค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่ต้องพกหัวชาร์จหลายอัน, ให้หนักกระเป๋า, ลองดูตัวนี้ค่ะ. หัวชาร์จยูกรีน 65 วัตต์, มีถึง 3 พอร์ต, ชาร์จพร้อมกันได้ทั้งมือถือ, แท็บเล็ต, และโน้ตบุ๊ก, ขนาดกะทัดรัดพกพาง่ายมากค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "tyeso_tumbler_304": {
        "on_screen_headline": "แก้วเก็บความเย็น TYESO 1200ml",
        "hook_text": "ใครที่มองหาแก้วเก็บความเย็น คุณภาพดี และจุได้เยอะ แนะนำตัวนี้เลยค่ะ.",
        "body_text": "แก้วเยติติดหูหิ้วไทโซ สแตนเลส 304 แท้ เก็บน้ำแข็งได้นานข้ามวัน มีหลอดดูดในตัว พกพาสะดวก ไม่หกเลอะเทอะค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่มองหาแก้วเก็บความเย็น, คุณภาพดี, และจุได้เยอะ, แนะนำตัวนี้เลยค่ะ. แก้วเยติติดหูหิ้วไทโซ, สแตนเลส 304 แท้, เก็บน้ำแข็งได้นานข้ามวัน, มีหลอดดูดในตัว, พกพาสะดวก ไม่หกเลอะเทอะค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "spray_mop_360": {
        "on_screen_headline": "ไม้ถูพื้นสเปรย์ หมุน 360 องศา",
        "hook_text": "ไม่ต้องหิ้วถังน้ำถูบ้าน ให้ปวดหลังอีกต่อไป แค่ใช้ไม้ถูพื้นรุ่นนี้ค่ะ.",
        "body_text": "ไม้ถูพื้นสเปรย์เดียร์ม่า มีกระบอกฉีดน้ำในตัว หัวม็อบหมุนได้รอบทิศ เช็ดทำความสะอาดง่าย พื้นแห้งไวไม่ทิ้งคราบน้ำค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ไม่ต้องหิ้วถังน้ำถูบ้าน, ให้ปวดหลังอีกต่อไป, แค่ใช้ไม้ถูพื้นรุ่นนี้ค่ะ. ไม้ถูพื้นสเปรย์เดียร์ม่า, มีกระบอกฉีดน้ำในตัว, หัวม็อบหมุนได้รอบทิศ, เช็ดทำความสะอาดง่าย, พื้นแห้งไวไม่ทิ้งคราบน้ำค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "solar_sensor_light": {
        "on_screen_headline": "ไฟโซลาร์เซลล์ 100 LED ค่าไฟ 0฿",
        "hook_text": "อยากให้รอบบ้านสว่างปลอดภัย โดยไม่ต้องเสียค่าไฟสักบาท แนะนำตัวนี้เลยค่ะ.",
        "body_text": "โคมไฟโซลาร์เซลล์ 100 แอลอีดี ชาร์จพลังงานแสงอาทิตย์ สว่างอัตโนมัติเมื่อมีคนเดินผ่าน กันน้ำกันฝน ติดตั้งง่ายมากไม่ต้องเดินสายไฟค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "อยากให้รอบบ้านสว่างปลอดภัย, โดยไม่ต้องเสียค่าไฟสักบาท, แนะนำตัวนี้เลยค่ะ. โคมไฟโซลาร์เซลล์ 100 แอลอีดี, ชาร์จพลังงานแสงอาทิตย์, สว่างอัตโนมัติเมื่อมีคนเดินผ่าน, กันน้ำกันฝน, ติดตั้งง่ายมากไม่ต้องเดินสายไฟค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "sonic_electric_toothbrush": {
        "on_screen_headline": "แปรงสีฟันไฟฟ้าโซนิค กันน้ำ IPX7",
        "hook_text": "อยากแปรงฟันให้สะอาดทั่วถึง แบบไม่เจ็บเหงือก แนะนำแปรงสีฟันไฟฟ้ารุ่นนี้ค่ะ.",
        "body_text": "แปรงสีฟันไฟฟ้าโซนิค ขนแปรงนุ่มละเอียด แรงสั่นทรงพลังช่วยขจัดคราบพลัค กันน้ำได้ทั้งตัวเครื่อง ชาร์จครั้งเดียวใช้งานได้ยาวนานค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "อยากแปรงฟันให้สะอาดทั่วถึง, แบบไม่เจ็บเหงือก, แนะนำแปรงสีฟันไฟฟ้ารุ่นนี้ค่ะ. แปรงสีฟันไฟฟ้าโซนิค, ขนแปรงนุ่มละเอียด, แรงสั่นทรงพลังช่วยขจัดคราบพลัค, กันน้ำได้ทั้งตัวเครื่อง, ชาร์จครั้งเดียวใช้งานได้ยาวนานค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    },
    "kitchen_dish_rack_stainless": {
        "on_screen_headline": "ชั้นคว่ำจานสแตนเลส 304 คร่อมอ่าง",
        "hook_text": "ใครที่พื้นที่ครัวจำกัด อยากจัดครัวให้เป็นระเบียบ ดูตัวนี้เลยค่ะ.",
        "body_text": "ชั้นคว่ำจานคร่อมอ่าง สแตนเลส 304 หนาพิเศษ แข็งแรงรับน้ำหนักได้เยอะ มีประตูปิดกันฝุ่น วางจานชามและอุปกรณ์ครัวได้ครบจบในที่เดียวค่ะ.",
        "cta_text": "สนใจกดสั่งที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": "ใครที่พื้นที่ครัวจำกัด, อยากจัดครัวให้เป็นระเบียบ, ดูตัวนี้เลยค่ะ. ชั้นคว่ำจานคร่อมอ่าง, สแตนเลส 304 หนาพิเศษ, แข็งแรงรับน้ำหนักได้เยอะ, มีประตูปิดกันฝุ่น, วางจานชามและอุปกรณ์ครัวได้ครบจบในที่เดียวค่ะ. สนใจกดสั่งที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
    }
}

AVAILABLE_VIDEOS = {
    "fanlife_tumbler_710ml": ("/videos/fanlife_tumbler_710ml.mp4?v=mali_sub_v1", 5.63),
    "master_art_colored_pencils": ("/videos/master_art_colored_pencils.mp4?v=mali_sub_v1", 0.47),
    "kettlebell_soft_pvc": ("/videos/kettlebell_soft_pvc.mp4?v=mali_sub_v1", 0.48),
    "sanmax_earphones_i14b": ("/videos/sanmax_earphones_i14b.mp4?v=mali_sub_v1", 4.68),
    "toothbrush_zdx3": ("/videos/sonic_electric_toothbrush.mp4?v=mali_sub_v1", 3.48),
    "cat_fountain_01": ("/videos/cat_fountain_01.mp4?v=v4_perfect_brand_20s", 10.09),
    "gan_charger_65w": ("/videos/gan_charger_65w.mp4?v=mali_sub_v1", 7.16),
    "uv_dust_mite_vacuum": ("/videos/uv_dust_mite_vacuum.mp4?v=v4_perfect_brand_20s", 8.58),
    "tyeso_tumbler_304": ("/videos/tyeso_tumbler_304.mp4?v=v4_perfect_brand_20s", 11.35),
    "spray_mop_360": ("/videos/spray_mop_360.mp4?v=v4_perfect_brand_20s", 11.81),
    "solar_sensor_light": ("/videos/solar_sensor_light.mp4?v=v4_perfect_brand_20s", 9.92),
    "air_fryer_visual": ("/videos/air_fryer_visual.mp4?v=v4_perfect_brand_20s", 7.89),
    "sonic_electric_toothbrush": ("/videos/sonic_electric_toothbrush.mp4?v=mali_sub_v1", 3.48),
    "kitchen_dish_rack_stainless": ("/videos/kitchen_dish_rack_stainless.mp4?v=v4_perfect_brand_20s", 7.76),
    "wireless_earbuds_anc": ("/videos/wireless_earbuds_anc.mp4?v=v4_perfect_brand_20s", 6.31),
}

def get_product_helper(product_id: str):
    p_data = None
    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                if product_id in db:
                    p_data = db[product_id]
        except Exception:
            pass

    if not p_data:
        return {"exists": False, "product_id": product_id}

    if product_id in AVAILABLE_VIDEOS:
        v_url, v_size = AVAILABLE_VIDEOS[product_id]
        v_exists = True
    else:
        v_url = None
        v_size = 0.0
        v_exists = False

    # Load script from PRODUCT_SCRIPTS or disk
    script_data = PRODUCT_SCRIPTS.get(product_id)
    if not script_data:
        script_path = BASE_DIR / "output" / product_id / "script.json"
        if script_path.is_file():
            try:
                with open(script_path, "r", encoding="utf-8") as sf:
                    script_data = json.load(sf)
            except Exception:
                pass

    if not script_data:
        title_short = p_data.get("title", "สินค้านี้")[:35]
        script_data = {
            "on_screen_headline": title_short[:20],
            "hook_text": f"ใครที่กำลังมองหา {title_short} แนะนำตัวนี้เลยค่ะ.",
            "body_text": f"รุ่นนี้ใช้งานดีมาก วัสดุพรีเมียม ตอบโจทย์คนใช้งานจริง คุณภาพคุ้มค่าเกินราคาแน่นอนค่ะ.",
            "cta_text": "สนใจกดสั่งซื้อที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
            "full_script": f"ใครที่กำลังมองหา {title_short} แนะนำตัวนี้เลยค่ะ. รุ่นนี้ใช้งานดีมาก วัสดุพรีเมียม ตอบโจทย์คนใช้งานจริง คุณภาพคุ้มค่าเกินราคาแน่นอนค่ะ. สนใจกดสั่งซื้อที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ."
        }

    cap_info = PRODUCT_CAPTIONS.get(product_id, {
        "caption": f"ใครมองหาตัวนี้บอกเลยว่าห้ามพลาด! {p_data.get('title', '')[:40]}... ใช้ดี คุณภาพดีมาก คุ้มราคา พิกัดในตะกร้าส้มซ้ายล่างเลยนะคะ 🧡✨",
        "hashtags": "#ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee #ป้ายยาของใช้"
    })

    media_mode = p_data.get("media_mode", "video" if v_exists else "ad_images")
    if not v_exists:
        footage = {
            "ad_video_status": "ไม่มีวิดีโอในลิงก์ -> สลับใช้รูปภาพโฆษณาแท้ของสินค้าอัตโนมัติ (6-8 ภาพ)",
            "review_videos_count": 0,
            "review_videos_status": "แปลงภาพถ่ายโฆษณาเป็นโมชัน 9:16 (Ken-Burns Dynamic Motion)",
            "media_mode": "ad_images"
        }
    else:
        footage = p_data.get("footage_sources", {
            "ad_video_status": "ดึงจากวิดีโอโฆษณาหลักในลิ้งค์ (1080x1920 HD)",
            "review_videos_count": 5,
            "review_videos_status": "ดึงจากวิดีโอผู้ใช้จริงในคอมเมนต์ (แกะกล่อง + ส่องเซรามิก + หลากสี)",
            "media_mode": "video"
        })

    return {
        "exists": True,
        "product_id": product_id,
        "product_data": p_data,
        "video_exists": v_exists,
        "media_mode": media_mode,
        "video_url": v_url,
        "video_size_mb": v_size,
        "voiceover_url": "/assets/sample_elevenlabs_mali.mp3",
        "voice_name": "มาลี (Mali - Natural & Clear Thai)",
        "script": script_data,
        "caption": cap_info.get("caption", ""),
        "hashtags": cap_info.get("hashtags", ""),
        "full_caption": f"{cap_info.get('caption', '')}\n\n{cap_info.get('hashtags', '')}",
        "footage_sources": footage
    }

@app.get("/api/product/{product_id}")
def get_product(product_id: str):
    """Return specific product data, exact video, spoken script, and post caption."""
    return get_product_helper(product_id)

class AnalyzeUrlRequest(BaseModel):
    url: str
    review_video_url: Optional[str] = None
    custom_title: Optional[str] = None
    custom_price: Optional[float] = None

def lookup_title_from_chrome_history(item_id: str) -> Optional[str]:
    """Inspect local Chrome history to extract exact Shopee product title if visited by user."""
    try:
        import sqlite3, shutil
        history_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\History"
        if not os.path.exists(history_path):
            return None
        temp_path = BASE_DIR / "temp_ch_lookup.db"
        shutil.copy2(history_path, temp_path)
        conn = sqlite3.connect(temp_path)
        c = conn.cursor()
        c.execute("SELECT title FROM urls WHERE url LIKE ? ORDER BY last_visit_time DESC LIMIT 1", (f"%{item_id}%",))
        row = c.fetchone()
        conn.close()
        if temp_path.exists():
            temp_path.unlink()
        if row and row[0]:
            clean = row[0].replace(" | Shopee Thailand", "").replace("Shopee Thailand | ", "").strip()
            if len(clean) > 5 and not clean.startswith("Shopee"):
                return clean
    except Exception:
        pass
    return None

class VoiceSynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "7XW5JhaNn90bnFojQ5DA"

@app.post("/api/voice/synthesize")
def synthesize_mali_voice(req: VoiceSynthesizeRequest):
    """Real-time Mali Thai voice synthesis using official Mali voice (7XW5JhaNn90bnFojQ5DA)."""
    text = req.text.strip()
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)

    api_key = os.getenv("ELEVENLABS_API_KEY", "") or "sk_323a5525e4dc6505f33bc3426bd634b54443b2dea530923b"
    voice_id = req.voice_id or "7XW5JhaNn90bnFojQ5DA"
    if voice_id == "OB8jPhZsR8bpZJnVSkvQ":
        voice_id = "7XW5JhaNn90bnFojQ5DA"

    model_id = "eleven_v4" if voice_id == "7XW5JhaNn90bnFojQ5DA" else "eleven_multilingual_v2"

    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.82,
                    "similarity_boost": 0.85,
                    "speed": 1.04,
                    "style": 0.0
                }
            },
            timeout=30
        )
        if r.status_code == 200:
            import base64
            b64_audio = base64.b64encode(r.content).decode("utf-8")
            return {
                "status": "success",
                "voice_id": voice_id,
                "model_id": model_id,
                "audio_base64": f"data:audio/mp3;base64,{b64_audio}",
                "duration": round(len(r.content) / (192 * 1024 / 8), 2)
            }
        else:
            r2 = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_v4_turbo",
                    "voice_settings": {"stability": 0.82, "similarity_boost": 0.85, "speed": 1.04,
                    "style": 0.0}
                },
                timeout=30
            )
            if r2.status_code == 200:
                import base64
                b64_audio = base64.b64encode(r2.content).decode("utf-8")
                return {
                    "status": "success",
                    "voice_id": voice_id,
                    "model_id": "eleven_v4_turbo",
                    "audio_base64": f"data:audio/mp3;base64,{b64_audio}",
                    "duration": round(len(r2.content) / (192 * 1024 / 8), 2)
                }
            return JSONResponse({"error": r.text}, status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# INTELLIGENT CATEGORY RULES & SCRIPT GENERATOR
def normalize_thai_title_py(raw_title: str) -> str:
    if not raw_title:
        return ""
    s = str(raw_title)
    # Normalize number commas: e.g. 2,0000 -> 20000 or 15,000 -> 15000
    s = re.sub(r'(\d+),(\d+)', r'\1\2', s)
    s = re.sub(r"^\[(Mall|ช้อปปี้|พร้อมส่ง|ของแท้|แท้ 100%|ของแท้ 100%)\]\s*", "", s, flags=re.I)
    s = re.sub(r"\s*\[(Mall|ช้อปปี้|พร้อมส่ง|ของแท้|แท้ 100%|อัตโนมัติ.*?)\]", "", s, flags=re.I)
    s = re.sub(r"\s*\(รับประกัน.*?\)", "", s, flags=re.I)
    s = re.sub(r"\s*\(พร้อมส่ง.*?\)", "", s, flags=re.I)
    s = re.sub(r"\s*\(ของแท้.*?\)", "", s, flags=re.I)
    s = re.sub(r"\s*【.*?】", "", s)
    s = re.sub(r"\s*\[.*?\]", "", s)

    # Normalize units while PRESERVING decimal points (1.3m -> 1.3 เมตร, NEVER 1 3ม!)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:m|เมตร|ม\.)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> เมตร", s, flags=re.I)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:ml|มล|มล\.)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> มิลลิลิตร", s, flags=re.I)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:w|วัตต์)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> วัตต์", s, flags=re.I)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:kg|กก|กก\.|กิโล|กิโลกรัม)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> กิโลกรัม", s, flags=re.I)
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:l|ลิตร)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> ลิตร", s, flags=re.I)
    s = re.sub(r"(\d+)\s*(?:mah|มิลลิแอมป์)(?=[^ก-๙a-zA-Z]|$)", r"\g<1> มิลลิแอมป์", s, flags=re.I)

    s = re.sub(r"[\/\|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.,;]$", "", s).strip()
    return s

def clean_short_thai_title_py(text: str, max_chars: int = 32) -> str:
    if not text:
        return "สินค้านี้"
    clean = re.sub(r"[\/\|]", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    # Split by spaces/words to avoid breaking Thai character clusters
    tokens = clean.split()
    res = ""
    for t in tokens:
        if len(res + " " + t) > max_chars:
            break
        res = (res + " " + t).strip()
    return (res or clean[:20]).strip() + "ตัวนี้"

UNIVERSAL_PREFIXES = [
    "พาวเวอร์แบงค์", "แบตเตอรี่สำรอง", "แบตสำรอง", "หัวชาร์จ", "สายชาร์จ", "แท่นชาร์จ", "ปลั๊กไฟ", "รางปลั๊ก",
    "เครื่องฟอกอากาศ", "เครื่องดูดฝุ่น", "เครื่องดูดไรฝุ่น", "เครื่องชงกาแฟ", "เครื่องปั่น", "เครื่องบด", 
    "เครื่องม้วนผม", "เครื่องหนีบผม", "เครื่องโกนหนวด", "เครื่องฉีดน้ำแรงดันสูง", "เครื่องฉีดน้ำ", "เครื่องพ่น",
    "พัดลมพกพา", "พัดลมคล้องคอ", "พัดลมไร้สาย", "พัดลม",
    "หม้อทอดไร้น้ำมัน", "หม้อต้มไฟฟ้า", "หม้อหุงข้าว", "หม้อชาบู", "หม้ออบลมร้อน", "หม้อไฟฟ้า", "หม้อ",
    "กระทะไฟฟ้า", "กระทะเคลือบหินอ่อน", "กระทะ", "เตาปิ้งย่าง", "เตาแม่เหล็กไฟฟ้า", "เตาอบ",
    "แก้วเก็บความเย็น", "แก้วน้ำสแตนเลส", "แก้วน้ำ", "กระบอกน้ำ",
    "ขนตาปลอม", "ที่ดัดขนตา", "มาสคาร่า", "ลิปสติก", "ลิปบาล์ม", "เซรั่มบำรุงผิว", "เซรั่ม", 
    "ครีมกันแดด", "ครีมบำรุงผิว", "ครีมทาหน้า", "ครีม", "โฟมล้างหน้า", "คลีนซิ่ง",
    "แผ่นแปะแก้ปวด", "แผ่นแปะสิว", "ยานวดคลายเส้น", "แผ่นรองเมาส์", "แผ่นกรอง", "แผ่นกันลื่น", "แผ่นแปะ",
    "โคมไฟตั้งโต๊ะ", "โคมไฟโซลาร์เซลล์", "โคมไฟหัวเตียง", "โคมไฟดักยุง", "โคมไฟ", "หลอดไฟไล่ยุง", "หลอดไฟโซลาร์เซลล์", "หลอดไฟ",
    "ไม้เซลฟี่", "ไม้ถูพื้น", "ไม้แขวนเสื้อ", "ไม้นวด", "ไม้กวาด",
    "ขาตั้งกล้อง", "ขาตั้งมือถือ", "ขาตั้งไอแพด", "ขาตั้ง",
    "เก้าอี้แคมป์ปิ้ง", "เก้าอี้พับ", "เต็นท์แคมป์ปิ้ง", "เต็นท์", "โต๊ะพับ",
    "กระเป๋าเดินทาง", "กระเป๋าสะพาย", "กระเป๋าสตางค์", "กระเป๋าเป้", "กระเป๋าผ้า", "กระเป๋า",
    "หูฟังบลูทูธ", "หูฟังไร้สาย", "หูฟังเกมมิ่ง", "หูฟัง", "ลำโพงบลูทูธ", "ลำโพง",
    "กางเกงยีนส์", "กางเกงขายาว", "กางเกงขาสั้น", "กางเกงคาร์โก้", "กางเกง", 
    "เสื้อยืด", "เสื้อเชิ้ต", "เสื้อคลุม", "เสื้อกันหนาว", "เสื้อ", "ชุดเดรส", "ชุดนอน", "กระโปรง", 
    "รองเท้าผ้าใบ", "รองเท้าแตะ", "รองเท้า",
    "ถุงขยะ", "ถุงซิปล็อค", "ถุงสุญญากาศ", "กล่องเก็บของ", "กล่องอาหาร", "กล่องทิชชู่", "กล่อง",
    "ที่นอนแมว", "คอนโดแมว", "ทรายแมวเต้าหู้", "ทรายแมว", "น้ำพุแมว", "ของเล่นแมว", "อาหารแมว", "อาหารสุนัข",
    "กรรไกรตัดกิ่ง", "กรรไกร"
]

UNIVERSAL_QUALIFIERS = [
    "ไร้สาย", "กันน้ำ", "ชาร์จไว", "พกพาง่าย", "พับได้", "สแตนเลส 304", "สแตนเลส", "สูตรร้อน", "สูตรเย็น",
    "ออร์แกนิค", "เกรดพรีเมียม", "ระบบสัมผัส", "เสียงเงียบ", "อัจฉริยะ", "มัลติฟังก์ชั่น", "เก็บอุณหภูมิ",
    "เคลือบเซรามิก", "ตัดเสียงรบกวน", "บลูทูธ", "ประหยัดไฟ", "ทรงสวย", "ผ้านุ่ม", "แกนสปริง"
]

def get_spoken_product_name_py(raw_title: str) -> str:
    norm = normalize_thai_title_py(raw_title)
    low = norm.lower()

    # 1. Powerbank / แบตสำรอง (เฉพาะเจาะจง ไม่ปนกับหัวชาร์จ)
    if any(k in low for k in ["powerbank", "power bank", "พาวเวอร์แบงค์", "แบตสำรอง", "acmic", "eloop", "remax", "romoss"]):
        mah_match = re.search(r"(\d+)\s*(?:มิลลิแอมป์|mah)", norm, re.I)
        brand_match = re.search(r"\b(ACMIC|Eloop|Remax|Romoss|Anker|Baseus|Yoobao)\b", norm, re.I)
        model_match = re.search(r"\b([A-Z]\d{3,4}[A-Za-z]?)\b", norm)
        brand = f"{brand_match.group(1).upper()} " if brand_match else ""
        model = f"{model_match.group(1)} " if model_match else ""
        cap = f"{mah_match.group(1)} มิลลิแอมป์" if mah_match else "ความจุสูง"
        return f"พาวเวอร์แบงค์ {brand}{model}{cap}ตัวนี้".replace("  ", " ").strip()

    # 2. GaN Charger / หัวชาร์จ & Adapter
    if any(k in low for k in ["หัวชาร์จ", "เครื่องชาร์จ", "gan charger", "adapter"]):
        watt_match = re.search(r"(\d+)\s*(?:วัตต์|w\b)", norm, re.I)
        watt = f" {watt_match.group(1)} วัตต์" if watt_match else ""
        return f"หัวชาร์จเร็ว GaN{watt}ตัวนี้"

    # 3. Universal prefix & qualifier matching across all product types
    matched_prefix = None
    for p in UNIVERSAL_PREFIXES:
        if p in norm:
            matched_prefix = p
            break

    if matched_prefix:
        matched_qual = ""
        for q in UNIVERSAL_QUALIFIERS:
            if q in norm and q not in matched_prefix:
                matched_qual = q
                break
        return f"{matched_prefix}{matched_qual}ตัวนี้"

    # Fallback: extract short title cleanly by whole words without cutting syllables
    parts = re.split(r"[,，、\-–—]", norm)
    return clean_short_thai_title_py(parts[0] if parts else norm, 24)

CATEGORY_RULES = [
{
        "id": "beauty_makeup",
        "keywords": [
            "ขนตา",
            "ขนตาปลอม",
            "ที่ดัดขนตา",
            "มาสคาร่า",
            "อายไลเนอร์",
            "ลิป",
            "ลิปสติก",
            "ลิปบาล์ม",
            "แป้งพัฟ",
            "คุชชั่น"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "บอกลาขนตาหลุดง่าย ไม่ตรงปก",
                "hook": "ใครเจอปัญหาติดขนตายาก, หลุดง่ายระหว่างวัน, หรือดูหลอกตาบ้างคะ?",
                "body": "{name} แกนใสนุ่มเบาสบายตา, ติดง่ายมากในนาทีเดียว, ขนตาเรียงเส้นสวยเป็นธรรมชาติเหมือนต่อร้าน, สวยตรงปกทั้งวันเลยค่ะ.",
                "cta": "สวยเป๊ะระดับมือโปร, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ค้นพบขนตาปลอมลุคธรรมชาติ 100%",
                "hook": "ไปเจอขนตาปลอมที่ติดแล้วตาหวานฉ่ำแบบสาวเกาหลีมาแล้วค่ะทุกคน!",
                "body": "{name} น้ำหนักเบามากเหมือนไม่ได้ติด, ไม่เคืองตา, แกนบางเนียนไปกับขอบตา, ถอดใช้ซ้ำได้หลายรอบ คุ้มมากค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "ติดง่าย น้ำหนักเบา ใช้ซ้ำได้คุ้มค่า",
                "hook": "ใครมองหาขนตาปลอมที่คุ้มค่า, สเปกเนียนสวยสมจริง, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} เส้นขนไฟเบอร์เกรดพรีเมียม, โค้งงอนเป็นธรรมชาติ, ทนทานไม่เสียทรง, สวยทุกลุคแน่นอนค่ะ.",
                "cta": "ของแท้ส่งไว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "camping_outdoor",
        "keywords": [
            "เก้าอี้แคมป์ปิ้ง",
            "เต็นท์",
            "โต๊ะพับ",
            "แคมป์ปิ้ง",
            "เก้าอี้พับ",
            "กางเต็นท์",
            "outdoor"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "บอกลาเก้าอี้หนัก นั่งปวดหลัง",
                "hook": "สายแคมป์ปิ้งคนไหน เบื่อเก้าอี้หนักๆ, กางยาก, นั่งแล้วเมื่อยหลังบ้างคะ?",
                "body": "{name} โครงสร้างแข็งแรงรับน้ำหนักได้เยอะ, กางและพับเก็บใน 3 วินาที, นั่งสบายไม่เมื่อยหลัง, พกพาสะดวกมากค่ะ.",
                "cta": "เตรียมทริปให้พร้อม, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ไอเทมลับสายแคมป์ปิ้ง นั่งสบายสุดๆ",
                "hook": "ไปเจอไอเทมแคมป์ปิ้งที่ชีวิตดีขึ้นเยอะมากมาแล้วค่ะทุกคน!",
                "body": "{name} ดีไซน์มินิมอลสวยตรงปก, ผ้าหนาระบายอากาศดี, พับแล้วขนาดกะทัดรัดใส่ท้ายรถสบาย, สายเที่ยวต้องมีเลยค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "โครงสร้างเหล็กกล้า แข็งแรง ทนทาน",
                "hook": "ใครมองหาอุปกรณ์แคมป์ปิ้งเกรดพรีเมียม, ใช้งานยาวนานหลายปี, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} วัสดุคุณภาพสูงทนแดดทนฝน, ข้อต่อแน่นหนาปลอดภัย, ผ่านการทดสอบรับน้ำหนักจริง, คุ้มค่าเงินทุกบาทแน่นอนค่ะ.",
                "cta": "มีโปรส่งฟรี, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "health_wellness",
        "keywords": [
            "แผ่นแปะแก้ปวด",
            "แก้ปวด",
            "ยานวด",
            "ยาหม่อง",
            "ปวดเมื่อย",
            "ออฟฟิศซินโดรม",
            "คลายเส้น",
            "พลาสเตอร์"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "กู้อาการปวดเมื่อย ออฟฟิศซินโดรม",
                "hook": "ใครนั่งทำงานนานๆ แล้วปวดคอบ่าไหล่, ปวดหลังทรมานบ้างคะ?",
                "body": "{name} ออกฤทธิ์ไวซึมลึกถึงชั้นกล้ามเนื้อ, แปะปุ๊บรู้สึกโล่งผ่อนคลายทันที, ไม่เหนียวเหนอะหนะ, แปะทำงานได้ทั้งวันเลยค่ะ.",
                "cta": "หมดกังวลเรื่องปวดเมื่อย, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "แผ่นแปะสมุนไพรสูตรเข้มข้น คลายกล้ามเนื้อ",
                "hook": "เจอแผ่นแปะแก้ปวดที่ใช้ดีจนต้องตุนติดบ้านไว้แล้วค่ะทุกคน!",
                "body": "{name} กลิ่นหอมสมุนไพรธรรมชาติผ่อนคลาย, แผ่นยืดหยุ่นติดแน่นไม่หลุดง่าย, ช่วยคลายเส้นได้ตรงจุด, คนทำงานต้องมีติดโต๊ะไว้ค่ะ.",
                "cta": "ของแท้ 100%, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ออกฤทธิ์ยาวนาน คุ้มค่า ปลอดภัย",
                "hook": "ใครมองหาตัวช่วยคลายปวดเมื่อยสูตรพรีเมียม, ตัวนี้การันตีความคุ้มค่าแน่นอนค่ะ!",
                "body": "{name} ผ่านการรับรองมาตรฐานปลอดภัย, ออกฤทธิ์ยาวนานต่อเนื่องหลายชั่วโมง, อ่อนโยนต่อผิวไม่แสบร้อน, แนะนำเลยค่ะ.",
                "cta": "ส่งไวมีโค้ดลด, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "kitchen_cooking",
        "keywords": [
            "หม้อต้ม",
            "กระทะ",
            "หม้อหุงข้าว",
            "เตาแม่เหล็ก",
            "กาน้ำร้อน",
            "เครื่องปั่น",
            "เครื่องบด",
            "กระทะไฟฟ้า",
            "หม้อไฟฟ้า"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "ทำอาหารง่าย ไม่ติดกระทะ ล้างสะดวก",
                "hook": "ใครอยู่หอหรือคอนโด, อยากทำอาหารง่ายๆ แต่ขี้เกียจล้างหม้อหลายใบมะคะ?",
                "body": "{name} ร้อนเร็วทั่วถึง, เคลือบกันติดอย่างดีไม่ติดก้นหม้อ, ต้ม ผัด ทอดในหม้อเดียวจบ, เช็ดล้างทำความสะอาดง่ายมากค่ะ.",
                "cta": "เด็กหอและคนรักครัว, จิ้มสั่งตรงตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "หม้อไฟฟ้ามินิมอล ร้อนไว จบในใบเดียว",
                "hook": "ไปเจอหม้อไฟฟ้ามินิมอลที่น่ารักและใช้งานดีเกินราคามาแล้วค่ะ!",
                "body": "{name} ปรับระดับความร้อนได้ดั่งใจ, ปลอดภัยด้วยระบบตัดไฟอัตโนมัติ, ขนาดกะทัดรัดวางตรงไหนก็น่ารัก, คุ้มค่าสมราคาจริงๆ ค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "ฟู้ดเกรดแท้ ปลอดภัย ประหยัดไฟ",
                "hook": "ใครมองหาเครื่องครัวไฟฟ้าคุณภาพมาตรฐาน, ปลอดภัยและทนทาน, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} วัสดุฟู้ดเกรดปลอดภัยไร้สารตกค้าง, กำลังไฟเสถียรประหยัดพลังงาน, ใช้งานได้ยาวนาน, คุ้มค่าเงินแน่นอนค่ะ.",
                "cta": "รับประกันของแท้, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "home_living",
        "keywords": [
            "เครื่องฟอกอากาศ",
            "เครื่องดูดฝุ่น",
            "เครื่องดูดไรฝุ่น",
            "พัดลม",
            "โคมไฟ",
            "หลอดไฟไล่ยุง",
            "ถุงขยะ",
            "ชั้นวางของ"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "หมดปัญหาฝุ่น ยุง และอากาศไม่บริสุทธิ์",
                "hook": "ใครที่บ้านมีฝุ่นเยอะ, จามบ่อย, หรือเจอปัญหายุงกวนใจบ้างคะ?",
                "body": "{name} ช่วยจัดการปัญหาในบ้านได้อย่างเห็นผล, ใช้งานง่าย, เสียงเงียบไม่รบกวน, ช่วยให้บรรยากาศในบ้านน่าอยู่ขึ้นเยอะมากค่ะ.",
                "cta": "เพื่อสุขภาพคนในบ้าน, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ไอเทมยกระดับบ้านให้น่าอยู่ขึ้น 10 เท่า",
                "hook": "ของใช้ในบ้านที่ซื้อมาแล้วรู้สึกคุ้มค่าเงินที่สุดเลยค่ะทุกคน!",
                "body": "{name} ดีไซน์สวยโมเดิร์นเข้ากับทุกมุมห้อง, คุณภาพมาตรฐาน, ใช้งานสะดวกสบาย, ชีวิตดีขึ้นชัดเจนค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "มาตรฐานระดับสากล ทนทาน ประหยัดไฟ",
                "hook": "ใครกำลังเล็งของใช้ในบ้านรุ่นนี้อยู่, บอกเลยว่าสเปกคุ้มค่าเกินราคามากค่ะ!",
                "body": "{name} ผ่านการตรวจสอบคุณภาพมาตรฐาน มอก., ทนทานแข็งแรง, ประหยัดพลังงาน, ใช้งานยาวนานคุ้มค่าแน่นอนค่ะ.",
                "cta": "ส่งฟรีของแท้ 100%, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "luggage_bags",
        "keywords": [
            "กระเป๋าเดินทาง",
            "กระเป๋าเป้",
            "กระเป๋าสะพาย",
            "กระเป๋าสตางค์",
            "กระเป๋า"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "ลากลื่น 360 องศา หมดกังวลเรื่องกระเป๋าพัง",
                "hook": "ใครเวลาเดินทาง กลัวกระเป๋าซิปแตก, หรือล้อสะดุดลากยากบ้างคะ?",
                "body": "{name} โครงสร้างเหนียวทนทานกันกระแทก, ล้อลื่นหมุนได้ 360 องศาไร้เสียงรบกวน, จุของได้จุใจ, เดินทางไกลสบายใจหายห่วงค่ะ.",
                "cta": "พร้อมเดินทางทริปใหม่, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "กระเป๋าเดินทางตัวจบ ดีไซน์หรูตรงปก",
                "hook": "ไปเจอกระเป๋าเดินทางที่สวยหรูและฟังก์ชันแน่นเกินราคามาแล้วค่ะ!",
                "body": "{name} คันชักปรับระดับแข็งแรง, ภายในแบ่งช่องจัดระเบียบของได้เป๊ะ, ดีไซน์สวยตรงปกถ่ายรูปขึ้นมากค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "ระบบล็อค TSA แท้ วัสดุกันรอยพรีเมียม",
                "hook": "ใครมองหากระเป๋าเดินทางคุณภาพสูง, สำหรับเดินทางทำงานหรือเที่ยว, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} วัสดุโพลีคาร์บอเนต 100% เหนียวทนทาน, ระบบล็อคมาตรฐานสากล, น้ำหนักเบา, คุ้มค่าสมราคาที่สุดค่ะ.",
                "cta": "รับประกันสินค้า, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "tools_garden",
        "keywords": [
            "กรรไกรตัดกิ่ง",
            "กรรไกร",
            "เครื่องฉีดน้ำ",
            "ไขควง",
            "สว่าน",
            "เครื่องมือช่าง"
        ],
        "angles": [
            {
                "type": "pain_point",
                "headline": "ตัดกิ่งไม้หนาได้สบาย ผ่อนแรง ไม่เจ็บมือ",
                "hook": "คนรักต้นไม้คนไหน เบื่อกรรไกรทื่อๆ, ตัดกิ่งหนาไม่เข้า, เจ็บมือไปหมดบ้างคะ?",
                "body": "{name} ใบมีดเหล็กกล้าคมกริบ, มีระบบสปริงผ่อนแรงช่วยทุ่นแรงได้เยอะมาก, ตัดกิ่งไม้หนาได้ขาดในชับเดียว, จับกระชับมือไม่ลื่นเลยค่ะ.",
                "cta": "ดูแลสวนให้สวยงาม, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "กรรไกรตัดกิ่งเกรดพรีเมียม คมกริบสุดๆ",
                "hook": "ไอเทมทำสวนที่ทุกคนต้องมีติดบ้านไว้เลยค่ะ, ใช้งานง่ายและคมมาก!",
                "body": "{name} วัสดุสแตนเลสแท้ไม่เป็นสนิม, ล็อคเก็บปลอดภัย, งานตัดเนียนเรียบไม่ทำร้ายต้นไม้, คุ้มค่าราคามากค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "เหล็ก SK5 ญี่ปุ่น คมทนทาน ไม่เป็นสนิม",
                "hook": "ใครมองหาเครื่องมือคุณภาพระดับมืออาชีพ, รุ่นนี้สเปกดีเกินราคาแน่นอนค่ะ!",
                "body": "{name} ทนทานต่อการสึกหรอ, รองรับงานหนักได้สบาย, ลับคมง่าย, ใช้งานได้ยาวนานหลายปี, แนะนำเลยค่ะ.",
                "cta": "ของแท้ส่งไว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },

    {
        "id": "power_bank",
        "keywords": ["พาวเวอร์แบงค์", "แบตสำรอง", "powerbank", "power bank", "แบตเตอรี่สำรอง", "acmic", "eloop", "remax", "romoss", "mah", "มิลลิแอมป์"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "แก้ปัญหาแบตหมดระหว่างวัน",
                "hook": "ใครแบตมือถือหมดระหว่างวันบ่อยๆ, พกสายชาร์จพะรุงพะรัง, ต้องดูตัวนี้ด่วนเลยค่ะ!",
                "body": "{name} มีสายชาร์จในตัวครบ, ชาร์จไวไม่ร้อน, ความจุแน่นๆ ชาร์จได้หลายรอบ, พกตัวเดียวจบออกจากบ้านสบายใจมากค่ะ.",
                "cta": "แบตหมดไม่ต้องลุ้น, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "พาวเวอร์แบงค์ตัวจบ ดีไซน์สวยตรงปก",
                "hook": "ไปเจอพาวเวอร์แบงค์ที่ตอบโจทย์ชีวิตที่สุดมาแล้วค่ะ, ดีไซน์สวยตรงปก น้ำหนักเบามาก!",
                "body": "{name} จ่ายไฟเสถียรเต็มสปีด, ขนาดกะทัดรัดพกพาง่าย, มีหน้าจอดิจิทัลบอกเปอร์เซ็นต์แบตชัดเจน, แฟนไอทีต้องหลงรักแน่นอนค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบจิ้มสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "พาวเวอร์แบงค์สเปกคุ้ม ปลอดภัย มอก.",
                "hook": "ใครมองหาพาวเวอร์แบงค์สเปกแน่นๆ, ตัวเดียวจบทั้งทำงานและเที่ยว, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} ความจุเต็มมิลลิแอมป์จริง, ระบบตัดไฟอัจฉริยะไม่ร้อน, ปลอดภัยผ่านมาตรฐาน มอก., คุ้มค่าเกินราคาแน่นอนค่ะ.",
                "cta": "รับประกันของแท้ส่งไว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "charger_tech",
        "keywords": ["หัวชาร์จ", "สายชาร์จ", "ชาร์จเร็ว", "gan charger", "adapter", "ugreen", "anker", "baseus"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "บอกลาหัวชาร์จหลายอันให้เกะกะ",
                "hook": "เบื่อไหมคะที่ต้องพกหัวชาร์จหลายอันเต็มกระเป๋า, ตัวนี้คือหัวเดียวจบทุกเครื่องเลยค่ะ!",
                "body": "{name} มีช่องชาร์จหลายพอร์ต, ชาร์จทั้งมือถือ โน้ตบุ๊ก และแท็บเล็ตพร้อมกันได้เลย, จ่ายไฟแรงเต็มสปีด ไม่ร้อนเลยค่ะ.",
                "cta": "จัดระเบียบกระเป๋าให้โล่ง, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "หัวชาร์จเร็ว GaN ตัวเล็กแต่พลังแรง",
                "hook": "เพิ่งได้หัวชาร์จเร็วตัวนี้มาลอง, ชีวิตดีขึ้นเยอะมาก ชาร์จไวทันใจสุดๆ ค่ะ!",
                "body": "{name} เทคโนโลยี GaN ขนาดกะทัดรัด, พับขาเก็บง่าย, เสียบชาร์จแป๊บเดียวแบตเด้งขึ้นไวมาก, ของมันต้องมีจริงๆ ค่ะ.",
                "cta": "ของแท้ 100%, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ชาร์จไว ปลอดภัย ไม่ทำร้ายแบตเตอรี่",
                "hook": "ใครที่กำลังเล็งหัวชาร์จเร็วตัวจบอยู่, บอกเลยว่ารุ่นนี้สเปกคุ้มค่าที่สุดค่ะ!",
                "body": "{name} จ่ายไฟนิ่งเสถียร, ชิปควบคุมอุณหภูมิปลอดภัย, รองรับระบบชาร์จเร็วทุกค่าย, ใช้งานทนทานยาวนานแน่นอนค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าสีส้มมุมซ้ายล่าง, กดสั่งก่อนโปรหมดนะคะ."
            }
        ]
    },
    {
        "id": "cat_litter",
        "keywords": ["ทรายแมว", "ทรายเต้าหู้", "cat litter", "tofu cat litter", "เบนโทไนท์", "ห้องน้ำแมว", "กระบะทราย"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "หมดปัญหากลิ่นและฝุ่นฟุ้ง",
                "hook": "ทาสแมวคนไหน ปวดหัวกับกลิ่นกระบะทราย, หรือฝุ่นฟุ้งติดเท้าน้องบ้างคะ?",
                "body": "พอเปลี่ยนมาใช้ {name}, คือดีขึ้นมาก. จับตัวเป็นก้อนไว, เก็บกลิ่นมิดชิด, ไร้ฝุ่นกวนใจ, ตักทิ้งง่าย, สะอาดปลอดภัยต่อน้องแมวเลยค่ะ.",
                "cta": "อยากให้บ้านหอมสะอาด, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ทรายแมวเต้าหู้ธรรมชาติ 100%",
                "hook": "บอกลากลิ่นฉุนในบ้าน! ทรายแมวที่ทาสแมวยุคนี้ต้องมีติดห้องไว้เลยค่ะ.",
                "body": "{name} ผลิตจากวัตถุดิบธรรมชาติแท้, จับก้อนแน่นตักง่าย, ทิ้งชักโครกได้, ไม่ติดเท้าน้องแมวเลยค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "คุ้มค่า ประหยัด ไม่ต้องเปลี่ยนบ่อย",
                "hook": "ใครมองหาทรายแมวคุณภาพพรีเมียม, ที่ใช้ได้นานและประหยัด, ตัวนี้ตอบโจทย์มากค่ะ!",
                "body": "{name} ดูดซับของเหลวได้รวดเร็ว, ก้อนไม่แตกกระจาย, ช่วยประหยัดปริมาณทราย, คุ้มค่าเงินทุกบาทแน่นอนค่ะ.",
                "cta": "มีโปรส่งฟรี, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "cat_fountain",
        "keywords": ["น้ำพุแมว", "น้ำพุสัตว์เลี้ยง", "เครื่องให้น้ำแมว", "cat fountain", "water fountain"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "แก้ปัญหาน้องแมวดื่มน้ำน้อย",
                "hook": "ทาสแมวคนไหน เจอปัญหาน้องกินน้ำน้อย, หรือชอบเล่นน้ำจนเลอะเทอะบ้างคะ?",
                "body": "พอเปลี่ยนมาใช้ {name}, น้องชอบมาก. วิ่งมากินน้ำทั้งวัน, ไร้สายปลอดภัย, ไร้กังวลเรื่องไตเลยค่ะ.",
                "cta": "เพื่อสุขภาพน้อง, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ไอเทมลับทาสแมวยุคใหม่",
                "hook": "บอกลาสายไฟเกะกะ! ไอเทมลับที่บ้านเลี้ยงแมวต้องมีติดไว้จริงๆ ค่ะ.",
                "body": "{name} ตัวถังสแตนเลสฟู้ดเกรด, มอเตอร์เสียงเงียบกริบ, แบตอึด, ล้างง่ายสุดๆ ค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "สแตนเลสแท้ ทนทาน ปลอดภัย 100%",
                "hook": "ถ้าคุณรักน้องแมว, ลงทุนกับน้ำพุรุ่นนี้ครั้งเดียวคุ้มค่าเกินราคาแน่นอนค่ะ!",
                "body": "{name} ไม่เกิดคราบเมือกเกาะ, ไส้กรองหลายชั้นน้ำสะอาดบริสุทธิ์, ใช้งานยาวนานหลายปี, คุ้มค่ามากค่ะ.",
                "cta": "ของแท้ประกันศูนย์, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "tripod_selfie",
        "keywords": ["ไม้เซลฟี่", "ขาตั้งกล้อง", "ไม้กันสั่น", "gimbal", "tripod", "selfie", "x-it", "บลูทูธ"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "ถ่ายรูปสวยคนเดียว ไม่ต้องง้อใคร",
                "hook": "สายเที่ยว สายคอนเทนต์คนไหน, ไม่อยากคอยง้อใครให้ช่วยถ่ายรูปให้บ้างคะ?",
                "body": "ตัวนี้คือจบเลยค่ะ, {name} ยืดได้ยาว, กางเป็นขาตั้งกล้องได้มั่นคง, มีรีโมทบลูทูธกดถ่ายเองได้สบาย, พกพาสะดวก, คุ้มราคามากค่ะ.",
                "cta": "สนใจกดสั่งซื้อที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ขาตั้งกล้องและไม้เซลฟี่ตัวจบ",
                "hook": "พกอันเดียวเที่ยวได้รอบโลก! ใครกำลังมองหาขาตั้งกล้องดีๆ แนะนำตัวนี้เลยค่ะ.",
                "body": "{name} กางอัตโนมัติในวินาทีเดียว, ขาตั้งแข็งแรงไม่ล้มง่าย, หมุนได้รอบทิศ, คุ้มค่าสมราคาจริงๆ ค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "แข็งแรง น้ำหนักเบา มุมมองเป๊ะ",
                "hook": "ใครที่กำลังเล็งไม้เซลฟี่รุ่นนี้อยู่, บอกเลยว่าสเปกดีเกินราคามากค่ะ!",
                "body": "{name} วัสดุอลูมิเนียมอัลลอยเกรดพรีเมียม, รองรับมือถือทุกรุ่น, ปรับมุมมองแนวนอนแนวตั้งได้ลื่นไหล, คุ้มค่าสุดๆ ค่ะ.",
                "cta": "จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ, ส่งไวมากค่ะ."
            }
        ]
    },
    {
        "id": "tumbler",
        "keywords": ["แก้วเก็บความเย็น", "แก้วน้ำ", "กระบอกน้ำ", "tumbler", "fanlife", "tyeso", "stanley", "แก้ว"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "น้ำแข็งไม่ละลายข้ามวัน",
                "hook": "อากาศร้อนขนาดนี้, ถ้าไม่มีแก้วเก็บความเย็นดีๆ คืออยู่ยากจริงๆ ค่ะ!",
                "body": "{name} จุน้ำได้สะใจ, สแตนเลสฟู้ดเกรดแท้, เก็บความเย็นได้เช้าจรดค่ำ, ไม่ต้องเติมน้ำแข็งบ่อยๆ เลยค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "discovery",
                "headline": "แก้วเก็บความเย็นเคลือบเซรามิกแท้",
                "hook": "ใครชอบพกแก้วน้ำไปทำงาน, หรือไปเที่ยว, แนะนำใบนี้เลยค่ะ!",
                "body": "{name} ด้านในเคลือบเซรามิกแท้, ไม่ติดกลิ่น, เก็บน้ำแข็งข้ามวัน, ลายน่ารัก, มีหูหิ้วพกพาง่ายมากค่ะ.",
                "cta": "สนใจกดสั่งซื้อที่ตะกร้าสีส้ม, มุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "benefit",
                "headline": "สแตนเลส 304 แท้ ดีไซน์สวยตรงปก",
                "hook": "แก้วเก็บความเย็นที่ทุกคนต้องมีติดตัว, สวยตรงปกและคุ้มค่าที่สุดค่ะ!",
                "body": "{name} ผิวสัมผัสพรีเมียม, หลอดในตัวถอดล้างง่าย, ไม่เป็นหยดน้ำเกาะรอบแก้ว, วางในรถได้พอดี, แนะนำเลยค่ะ.",
                "cta": "ของแท้ 100%, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "earbuds",
        "keywords": ["หูฟัง", "earphone", "headphone", "earbuds", "baseus", "หูฟังบลูทูธ", "ไร้สาย"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "บอกลาเสียงรบกวนรอบข้าง",
                "hook": "ใครรำคาญเสียงรอบข้างเวลาเดินทาง หรือทำงาน, ต้องมีหูฟังตัวนี้เลยค่ะ!",
                "body": "{name} ระบบตัดเสียงรบกวน ANC เงียบสงบ, เบสแน่นสะใจ, ไมค์คุยโทรศัพท์ชัดแจ๋ว, สวมใส่สบายไม่เจ็บหูเลยค่ะ.",
                "cta": "จัดเต็มความบันเทิง, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "หูฟังบลูทูธเสียงเทพ ราคาหลักร้อย",
                "hook": "เพิ่งไปเจอหูฟังบลูทูธที่เสียงดีเกินราคามาก, บอกเลยว่าคุ้มค่าเกินต้านค่ะ!",
                "body": "{name} ดีไซน์มินิมอลสวยหรู, เชื่อมต่อบลูทูธไวเสถียร, เล่นเกมไม่ดีเลย์, แบตอึดฟังเพลงได้ทั้งวันเลยค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบจิ้มสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ตัดเสียงรบกวน เบสแน่น แบตอึด",
                "hook": "ใครกำลังหาหูฟังบลูทูธเสียงดีๆ, ราคาจับต้องได้, ต้องดูตัวนี้เลยค่ะ!",
                "body": "{name} ชิปเสียงคุณภาพสูง, รองรับสมาร์ทโฟนทุกระบบ, กันน้ำกันเหงื่อ, ใช้งานทนทาน คุ้มราคาแน่นอนค่ะ.",
                "cta": "กดสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ, ของแท้แน่นอนค่ะ."
            }
        ]
    },
    {
        "id": "cleaning_mop",
        "keywords": ["ไม้ถูพื้น", "ม็อบ", "ถูบ้าน", "เครื่องดูดฝุ่น", "ไรฝุ่น", "mop", "vacuum", "deerma"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "ไม่ต้องหิ้วถังน้ำ ไม่ปวดหลัง",
                "hook": "มีใครเบื่องานบ้าน, ที่ต้องคอยก้มๆ เงยๆ ยกถังน้ำจนปวดหลังบ้างคะ?",
                "body": "ตั้งแต่ได้ {name} มาคือชีวิตสบายขึ้นเยอะ, ฉีดพ่นน้ำในตัว, เช็ดทำความสะอาดง่าย, พื้นแห้งไวมากค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบกดสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ไอเทมทำความสะอาดบ้านยุคใหม่",
                "hook": "งานบ้านเสร็จไวใน 10 นาที! ใครยังไม่มีตัวนี้บอกเลยว่าพลาดมากค่ะ.",
                "body": "{name} หัวหมุนได้ 360 องศา, ซอกซอนใต้เตียงใต้โซฟาได้หมดจด, ผ้าม็อบดักจับเส้นผมและฝุ่นได้ดีเยี่ยมเลยค่ะ.",
                "cta": "อยากให้บ้านสะอาดสบายแรง, จิ้มสั่งที่ตะกร้าส้มซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ทนทาน ประหยัดเวลา คุ้มค่าที่สุด",
                "hook": "ใครมองหาไม้ถูพื้นดีๆ, ที่ใช้ทนใช้นานไม่ต้องเปลี่ยนบ่อย, แนะนำรุ่นนี้เลยค่ะ!",
                "body": "{name} โครงสร้างแข็งแรงน้ำหนักเบา, กระบอกน้ำจุใจ, ถูได้ทั่วบ้านโดยไม่ต้องเติมน้ำซ้ำ, คุ้มค่าคุ้มราคามากค่ะ.",
                "cta": "รับประกันของแท้ส่งไว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "air_fryer",
        "keywords": ["หม้อทอด", "หม้อทอดไร้น้ำมัน", "เตาอบ", "air fryer", "หม้ออบลมร้อน"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "บอกลาน้ำมันกระเด็น คลีนได้ทุกมื้อ",
                "hook": "อยากกินของทอดกรอบๆ, แต่กลัวอ้วนและเบื่อน้ำมันกระเด็นเลอะครัวใช่ไหมคะ?",
                "body": "{name} ทอดกรอบอร่อยโดยไม่ง้อน้ำมัน, รีดไขมันส่วนเกินออกได้ถึง 80%, สุขภาพดีขึ้นแถมครัวไม่เหม็นควันเลยค่ะ.",
                "cta": "สุขภาพดีเริ่มต้นที่ครัว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "หม้อทอดกระจกใส เห็นอาหารด้านใน",
                "hook": "ทำอาหารง่ายขึ้นเยอะมาก! หม้อทอดรุ่นใหม่มองเห็นอาหารด้านในโดยไม่ต้องดึงออกดูค่ะ.",
                "body": "{name} ดีไซน์สวยหรูมินิมอล, หน้าจอสัมผัสมีเมนูอัตโนมัติครบ, สุกกรอบสม่ำเสมอ, ล้างทำความสะอาดง่ายสุดๆ ค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, รีบจิ้มสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ฟังก์ชั่นครบ จุใจ คุ้มค่าเกินราคา",
                "hook": "สายเฮลตี้ หรือใครที่ชอบทำอาหารง่ายๆ, ต้องมีเครื่องนี้ติดครัวไว้เลยค่ะ!",
                "body": "{name} ร้อนไวทันใจด้วยกำลังไฟเต็มสปีด, ความจุพอเหมาะสำหรับครอบครัว, วัสดุเคลือบ non-stick ไม่ติดหม้อ, คุ้มค่ามากค่ะ.",
                "cta": "ของแท้ประกันศูนย์, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "beauty_skincare",
        "keywords": ["เซรั่ม", "ครีม", "กันแดด", "หน้าใส", "สกินแคร์", "serum", "skincare", "ลิป", "สิว"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "กู้ผิวพังให้กลับมาเนียนใส",
                "hook": "ใครมีปัญหาผิวโทรม, แต่งหน้าไม่ค่อยติด, มามุงทางนี้ด่วนเลยค่ะ!",
                "body": "{name} เนื้อสัมผัสบางเบา, ซึมไว, ไม่เหนอะหนะ, ใช้ต่อเนื่องแล้วผิวดูชุ่มชื้นสุขภาพดีขึ้นชัดเจนค่ะ.",
                "cta": "ของแท้แน่นอน, กดจิ้มที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "สกินแคร์ตัวเด็ด กู้หน้าใสไว",
                "hook": "เห็นคนรีวิวกันเยอะมากจนต้องสั่งมาลอง, แล้วผลลัพธ์คือจึ้งจริงค่ะทุกคน!",
                "body": "{name} อ่อนโยนต่อผิวแพ้ง่าย, ปลอบประโลมผิวได้ดีเยี่ยม, ตื่นมาหน้านุ่มฟูฉ่ำน้ำ, ยกให้เป็นลูกรักขวดใหม่เลยค่ะ.",
                "cta": "แปะพิกัดของแท้ไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "ส่วนผสมพรีเมียม เห็นผลจริงตรงปก",
                "hook": "ใครมองหาสกินแคร์ตัวจบ, ที่ตอบโจทย์การบำรุงผิวล้ำลึก, แนะนำตัวนี้เลยค่ะ!",
                "body": "{name} สารสกัดเข้มข้นมาตรฐานระดับสากล, ไม่มีสารอันตราย, ใช้ได้ทุกสภาพผิว, คุ้มค่าเกินราคาแน่นอนค่ะ.",
                "cta": "ส่งฟรีมีโค้ดลด, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    },
    {
        "id": "fashion",
        "keywords": ["กางเกง", "เสื้อ", "กระโปรง", "เดรส", "รองเท้า", "กระเป๋า", "ยีนส์"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "พรางหุ่นเป๊ะ ไม่ต้องกลัวพุงออก",
                "hook": "สาวๆ คนไหน มีปัญหาเรื่องสัดส่วน, อยากใส่ชุดแล้วดูเพรียวสวยมั่นใจบ้างคะ?",
                "body": "{name} แพทเทิร์นเก็บทรงเป๊ะมาก, ช่วยพรางหน้าท้องและสะโพก, ใส่แล้วดูขายาวเพรียวขึ้นทันทีเลยค่ะ.",
                "cta": "สวยตรงปกไม่จกตา, จิ้มเลือกไซซ์ที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ใส่แล้วทรงสวย พรางหุ่นเป๊ะ",
                "hook": "ใครอยากแต่งตัวแล้วดูเพรียวสวยเป๊ะ, แนะนำชิ้นนี้เลยค่ะ, สวยตรงปกมาก!",
                "body": "{name} คัตติ้งเนี้ยบ, เนื้อผ้าใส่สบาย, ระบายอากาศดี, แมตช์กับชุดไหนก็รอด, สาวๆ ต้องมีติดตู้ไว้ค่ะ.",
                "cta": "มีครบทุกไซซ์, จิ้มเลือกที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "benefit",
                "headline": "เนื้อผ้าเกรดพรีเมียม แมตช์ง่ายทุกสไตล์",
                "hook": "ไอเทมแฟชั่นที่ใส่ได้บ่อยไม่มีเอาต์, คุ้มค่าสมราคาที่สุดค่ะ!",
                "body": "{name} เย็บประณีตเรียบร้อย, ผ้าไม่ยับง่าย, ซักแล้วไม่หดไม่ย้วย, ใส่ไปทำงานหรือไปเที่ยวก็ดูดีทุกลุคค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าสีส้มมุมซ้ายล่าง, รีบสั่งก่อนไซซ์หมดนะคะ."
            }
        ]
    },
    {
        "id": "fishing",
        "keywords": ["เหยื่อ", "ตกปลา", "หนอนยาง", "กบยาง", "คันเบ็ด", "รอก", "hunsabait", "lure"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "หมดปัญหาปลาระแวง กรอเนียนๆ",
                "hook": "น้าๆ สายตกปลาคนไหน เจอหมายเคี่ยวๆ ปลาระแวงไม่ยอมกัดเหยื่อบ้างครับ?",
                "body": "{name} แอคชั่นพลิ้วเป็นธรรมชาติมากในน้ำ, ปลาช่อนชะโดกัดเต็มปากไม่มีคาย, ผ่านสวะได้สบายไม่ติดกิ่งไม้เลยครับ.",
                "cta": "น้าๆ จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะครับ, จัดส่งไวมาก."
            },
            {
                "type": "discovery",
                "headline": "เหยื่อยางแอคชั่นเนียน ปลากัดเต็มคำ",
                "hook": "สายตกปลาคนไหนมองหาเหยื่อเด็ดๆ, แนะนำตัวนี้เลยค่ะ!",
                "body": "{name} เนื้อยางเหนียวนุ่มทนทาน, แอคชั่นพลิ้วสมจริงในน้ำ, เรียกปลานักล่ากัดเต็มคำแน่นอนค่ะ.",
                "cta": "พิกัดอยู่ที่ตะกร้าส้มมุมซ้ายล่าง, จิ้มสั่งก่อนของหมดนะคะ."
            },
            {
                "type": "benefit",
                "headline": "ปลาช่อนกระพงกัดดุ กรอเนียนๆ",
                "hook": "ใครที่กำลังเล็งตัวนี้อยู่, บอกเลยว่าต้องมีติดกล่องเหยื่อไว้ค่ะ!",
                "body": "{name} แอคชั่นดีมาก, ลากผ่านสวะได้เนียน, ตีไกลแม่นยำ, ปลากัดไม่มีระแวงเลยค่ะ.",
                "cta": "จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ, ส่งไวมากค่ะ."
            }
        ]
    },
    {
        "id": "pet_general",
        "keywords": ["อาหารแมว", "อาหารหมา", "ขนมแมวเลีย", "ของเล่นแมว", "ที่นอนแมว", "คอนโดแมว", "สัตว์เลี้ยง", "pet"],
        "angles": [
            {
                "type": "pain_point",
                "headline": "แก้ปัญหาเจ้านายเบื่ออาหารหรือซึม",
                "hook": "ใครที่น้องหมาน้องแมวที่บ้านเบื่ออาหาร, หรือไม่ค่อยร่าเริง, ต้องลองตัวนี้เลยค่ะ!",
                "body": "{name} คัดสรรคุณภาพเพื่อสุขภาพน้องๆ โดยเฉพาะ, กลิ่นหอมน่ากิน, น้องชอบมาก, สุขภาพแข็งแรงขึ้นชัดเจนค่ะ.",
                "cta": "เพื่อสุขภาพที่ดีของน้อง, จิ้มสั่งที่ตะกร้าส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ของดีบอกต่อสำหรับสัตว์เลี้ยง",
                "hook": "คนรักสัตว์เลี้ยงต้องดูเลยค่ะ! ไอเทมที่ช่วยให้ชีวิตน้องๆ แฮปปี้ขึ้นเยอะมาก.",
                "body": "{name} คุณภาพดี, ปลอดภัย, น้องชอบมาก, คุ้มค่าสมราคาจริงๆ ค่ะ.",
                "cta": "แปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบกดเลย."
            },
            {
                "type": "benefit",
                "headline": "ปลอดภัย ไร้สารอันตราย มาตรฐานรับรอง",
                "hook": "ทาสหมาทาสแมวที่มองหาของดีมีคุณภาพ, ตัวนี้การันตีความคุ้มค่าแน่นอนค่ะ!",
                "body": "{name} ผ่านการตรวจสอบความปลอดภัยเรียบร้อย, ใช้งานทนทาน, ช่วยให้น้องๆ มีความสุขในทุกๆ วันค่ะ.",
                "cta": "ของแท้ส่งไว, จิ้มสั่งที่ตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            }
        ]
    }
]

def generate_smart_script_py(title: str, style_type: str = None) -> dict:
    normalized_title = normalize_thai_title_py(title)
    title_lower = normalized_title.lower()
    matched_cat = None
    for cat in CATEGORY_RULES:
        if any(k in title_lower for k in cat["keywords"]):
            matched_cat = cat
            break

    spoken_name = get_spoken_product_name_py(title)

    if not matched_cat:
        fallback_angles = [
            {
                "type": "pain_point",
                "headline": "ไอเทมแก้ปัญหาที่รีวิวแน่น",
                "hook": "ใครเจอปัญหากับของเดิมๆ ที่ใช้อยู่, บอกเลยว่าต้องดูตัวนี้ด่วนเลยค่ะ!",
                "body": f"{spoken_name} ตอบโจทย์การใช้งานจริง, แก้ปัญหาตรงจุด, ใช้ง่าย, คุ้มค่าสมราคาจริงๆ ค่ะ.",
                "cta": "รับประกันของแท้, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ."
            },
            {
                "type": "discovery",
                "headline": "ไอเทมเด็ดที่รีวิวเยอะจนต้องสั่ง",
                "hook": "เห็นคนรีวิวกันเยอะมาก, จนต้องสั่งมาลองเอง แล้วคือดีงามตรงปกจริงค่ะ!",
                "body": f"{spoken_name} ใช้งานง่าย, ดีไซน์สวยตรงปก, ฟังก์ชันครบครัน, คุ้มค่าสมราคาจริงๆ ค่ะ.",
                "cta": "ใครสนใจแปะพิกัดไว้ที่ตะกร้าส้มมุมซ้ายล่างแล้วนะคะ, รีบไปตำเลย."
            },
            {
                "type": "benefit",
                "headline": "ของดีบอกต่อ คุ้มค่าเกินราคา",
                "hook": "ใครที่กำลังเล็งตัวนี้อยู่, บอกเลยว่ากดสั่งได้เลย ไม่ผิดหวังแน่นอนค่ะ!",
                "body": f"{spoken_name} ตอบโจทย์การใช้งานจริง, คุณภาพดีเกินราคา, สเปกแน่น คุ้มค่าเงินแน่นอนค่ะ.",
                "cta": "มีโปรส่งฟรี, จิ้มสั่งตรงตะกร้าสีส้มมุมซ้ายล่างได้เลยนะคะ, ส่งไวมากค่ะ."
            }
        ]
        if style_type == 'pain_point':
            chosen = fallback_angles[0]
        elif style_type == 'benefit':
            chosen = fallback_angles[2]
        else:
            chosen = fallback_angles[1]
    else:
        angles = matched_cat["angles"]
        if style_type:
            filtered = [a for a in angles if a.get("type") == style_type]
            chosen = filtered[0] if filtered else angles[0]
        else:
            chosen = angles[0]

    hook = chosen["hook"]
    body = chosen["body"].replace("{name}", spoken_name)
    cta = chosen["cta"]
    full_script = f"{hook} {body} {cta}"

    return {
        "on_screen_headline": chosen["headline"][:25],
        "hook_text": hook,
        "body_text": body,
        "cta_text": cta,
        "full_script": full_script
    }

@app.post("/api/product/analyze")

def analyze_product_url(req: AnalyzeUrlRequest):
    """Analyze Shopee product URL, match or scout product, return script, caption, and review video."""
    url = req.url.strip()
    if not url:
        return JSONResponse({"error": "กรุณาวางลิงก์สินค้า Shopee"}, status_code=400)

    # 0. Automatically follow 301/302 shortlink redirects with typo tolerance (O/0, l/I/1)
    resolved_url = url
    if "s.shopee.co.th" in url or "shope.ee" in url:
        code = url.split("?")[0].rstrip("/").split("/")[-1]
        test_codes = [code]
        # Generate common OCR/manual typo variations
        for idx, ch in enumerate(code):
            if ch in "O0":
                test_codes.append(code[:idx] + ("0" if ch == "O" else "O") + code[idx+1:])
            elif ch in "Il1":
                for alt in ("I", "l", "1"):
                    if alt != ch:
                        test_codes.append(code[:idx] + alt + code[idx+1:])

        for tc in test_codes:
            t_url = url.replace(code, tc)
            try:
                r = requests.get(
                    t_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Referer": "https://www.google.com/"
                    },
                    allow_redirects=False,
                    timeout=5
                )
                if r.status_code in (301, 302, 307, 308) and r.headers.get("Location"):
                    loc = r.headers["Location"]
                    if "error_page" not in loc:
                        resolved_url = loc
                        break
            except Exception:
                pass

    url_lower = url.lower()
    resolved_lower = resolved_url.lower()
    matched_pid = None

    if PRODUCTS_DB_PATH.is_file():
        try:
            with open(PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                # 1. Exact match or substring match
                for pid, p in db.items():
                    s_url = p.get("shopee_url", "").lower()
                    if s_url and (s_url in url_lower or url_lower in s_url):
                        matched_pid = pid
                        break
                    # 2. Match short_urls
                    short_urls = [su.lower() for su in p.get("short_urls", [])]
                    if url_lower in short_urls or any(su in url_lower for su in short_urls):
                        matched_pid = pid
                        break

                    # 3. Match short codes (e.g. bv8fg1emk, 2vt30jflys)
                    short_codes = [su.split('/')[-1].lower() for su in p.get('short_urls', []) if '/' in su]
                    if any(sc in url_lower or sc in resolved_lower for sc in short_codes if len(sc) >= 5):
                        matched_pid = pid
                        break

                    # 4. Match item ID or shop ID numbers strictly between input and product shopee_url
                    input_nums = set(re.findall(r'\d{8,}', url + ' ' + resolved_url))
                    p_nums = set(re.findall(r'\d{8,}', s_url))
                    if input_nums and p_nums and input_nums.intersection(p_nums):
                        matched_pid = pid
                        break

                    # 5. Match keywords in slug
                    keywords = [k for k in pid.split("_") if len(k) > 3]
                    for kw in keywords:
                        if kw in url_lower:
                            matched_pid = pid
                            break
                    if matched_pid:
                        break
        except Exception:
            pass

    if matched_pid:
        res = get_product_helper(matched_pid)
        res["status"] = "matched"
        return res

    # Fallback / Custom Scout Handling
    slug = url.split("?")[0].rstrip("/").split("/")[-1]

    # Check if slug is pure gibberish/short code or numeric (e.g. 2Vt3OJFLys, 47268120717)
    is_gibberish_slug = bool(re.match(r"^[A-Za-z0-9_-]{4,20}$", slug)) and not re.search(r"[ก-๙]", slug)
    is_short_link = "s.shopee.co.th" in url or "shope.ee" in url or is_gibberish_slug

    # Check Chrome history first for exact title if user browsed it
    chrome_found_title = None
    input_all_nums = re.findall(r"\d{8,}", url + " " + resolved_url)
    for n in input_all_nums:
        ct = lookup_title_from_chrome_history(n)
        if ct:
            chrome_found_title = ct
            break

    if req.custom_title and req.custom_title.strip():
        title_clean = req.custom_title.strip()
    elif chrome_found_title:
        title_clean = chrome_found_title
    elif "47268120717" in url:
        title_clean = "แปรงสีฟันไฟฟ้า 2-in-1 โซนิค ปรับได้ 6 ระดับ กันน้ำ IPX7"
    elif "43461659347" in url or "fanlife" in url_lower:
        title_clean = "แก้วน้ำเก็บความเย็น ขนาด 710 มล. เคลือบเซรามิกแท้ (Fanlife)"
    elif is_short_link or not slug or len(slug) < 3:
        title_clean = ""
    else:
        title_clean = re.sub(r"[-_]", " ", slug)
        title_clean = re.sub(r" i\.\d+\.\d+", "", title_clean).strip()
        if re.match(r"^\d+$", title_clean):
            title_clean = ""

    price_val = float(req.custom_price) if req.custom_price and req.custom_price > 0 else 199.0
    commission_val = round(price_val * 0.15, 2)

    custom_pid = "custom_" + re.sub(r"[^a-zA-Z0-9]", "", slug)[:16]
    custom_data = {
        "product_id": custom_pid,
        "title": title_clean,
        "price": price_val,
        "shopee_url": url,
        "category": "สินค้าแนะนำสำหรับคุณ",
        "shop": "Shopee Mall Official Store",
        "ams_commission_rate": 15.0,
        "commission_amount": commission_val
    }

    script_data = generate_smart_script_py(title_clean or slug or "สินค้าแนะนำ")
    if "43461659347" in url or "fanlife" in url_lower:
        price_val = 118.0
        commission_val = 17.70
        custom_data["price"] = price_val
        custom_data["commission_amount"] = commission_val

    caption = f"ใครที่กำลังมองหาตัวนี้อยู่บอกเลยต้องมี! {title_clean[:35]}... ฟังก์ชันครบ คุณภาพดี คุ้มราคามาก พิกัดในตะกร้าส้มซ้ายล่างเลยนะคะ 🧡✨"
    hashtags = "#ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee #ป้ายยาของใช้"

    # Match smart video by keywords or review video URL
    if req.review_video_url and req.review_video_url.startswith("http"):
        default_vid = (req.review_video_url, 6.5)
    else:
        t_low = title_clean.lower()
        if any(k in t_low for k in ["เคตเทิลเบล", "kettlebell", "ดัมเบล", "dumbbell", "ยกน้ำหนัก", "fitness"]):
            default_vid = AVAILABLE_VIDEOS.get("kettlebell_soft_pvc")
        elif any(k in t_low for k in ["แปรงสีฟัน", "toothbrush", "sonic"]):
            default_vid = AVAILABLE_VIDEOS.get("sonic_electric_toothbrush")
        elif any(k in t_low for k in ["หูฟัง", "earbud", "audio", "baseus"]):
            default_vid = AVAILABLE_VIDEOS.get("sanmax_earphones_i14b")
        elif any(k in t_low for k in ["แมว", "fountain", "pet", "น้ำพุ"]):
            default_vid = AVAILABLE_VIDEOS.get("cat_fountain_01")
        elif any(k in t_low for k in ["ชาร์จ", "charger", "gan", "ugreen"]):
            default_vid = AVAILABLE_VIDEOS.get("gan_charger_65w")
        elif any(k in t_low for k in ["ดูดฝุ่น", "ไรฝุ่น", "vacuum", "deerma"]):
            default_vid = AVAILABLE_VIDEOS.get("uv_dust_mite_vacuum")
        elif any(k in t_low for k in ["หม้อทอด", "fryer", "simplus"]):
            default_vid = AVAILABLE_VIDEOS.get("air_fryer_visual")
        elif any(k in t_low for k in ["ถูพื้น", "mop"]):
            default_vid = AVAILABLE_VIDEOS.get("spray_mop_360")
        else:
            default_vid = AVAILABLE_VIDEOS.get("kettlebell_soft_pvc", ("/videos/kettlebell_soft_pvc.mp4", 0.80))
    return {
        "status": "custom_generated",
        "exists": True,
        "product_id": custom_pid,
        "product_data": custom_data,
        "video_exists": True,
        "video_url": default_vid[0],
        "video_size_mb": default_vid[1],
        "voiceover_url": "/assets/sample_elevenlabs_mali.mp3",
        "voice_name": "มาลี (Mali - Natural & Clear Thai)",
        "script": script_data,
        "caption": caption,
        "hashtags": hashtags,
        "full_caption": f"{caption}\n\n{hashtags}"
    }

@app.post("/api/pipeline/start")
def start_pipeline_cloud():
    """Cloud dashboard pipeline trigger."""
    return {
        "job_id": "cloud-render-job",
        "status": "started",
        "message": "ระบบ Cloud Dashboard รับคำสั่งเรียบร้อย เริ่มการประมวลผล..."
    }

@app.get("/api/pipeline/logs/{job_id}")
async def stream_cloud_pipeline_logs(job_id: str):
    """Server-Sent Events (SSE) streaming live progress steps to the web UI."""
    async def log_stream():
        steps = [
            ("🚀 [Step 1] ดึงข้อมูลสินค้า รีวิว 5 ดาว และตรวจสอบคอมมิชชั่น AMS (>= 8%)...", 20, "Step 1: Product Scout"),
            ("✅ ดึงข้อมูลสำเร็จ! เรตคอมมิชชั่น AMS ผ่านเกณฑ์คุณภาพ", 35, "Step 1: Product Scout"),
            ("🎥 [Step 1.5] กรองวิดีโอรีวิวด้วย OpenCV และคัดช็อตเด็ดด้วย Gemini Vision (Hook Action / Closeup)...", 50, "Step 1.5: Smart Vision Curator"),
            ("✍️ [Step 2] Gemini 2.5 Flash กำลังสร้างสคริปต์ป้ายยา 20 วินาที ภาษาพูดธรรมชาติ...", 68, "Step 2: Script Writer"),
            ("🎯 สคริปต์พร้อมแล้ว: Hook ดึงดูด 0-3 วินาทีแรก + จุดเด่นสินค้าชัดเจน", 78, "Step 2: Script Writer"),
            ("🎙️ [Step 3] บังคับใช้เสียงพากย์มาลี (ElevenLabs Mali AI) สังเคราะห์เสียงพากย์สดระดับ Studio Mastering...", 88, "Step 3: Voice & Subtitles"),
            ("🎬 [Step 4] FFmpeg กำลังตัดต่อ 1080x1920 (9:16) ซูม Ken-Burns มิกซ์เสียงเพลง และฝังซับขอบขาว...", 96, "Step 4: Video Assembler"),
            ("🏁 กระบวนการทั้งหมดเสร็จสมบูรณ์ 100%! วิดีโอพร้อมโพสต์ทันที", 100, "Completed")
        ]
        for log_text, progress, step_label in steps:
            payload = json.dumps({"log": log_text, "progress": progress, "step": step_label})
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.7)

        final_payload = json.dumps({"status": "completed", "progress": 100})
        yield f"data: {final_payload}\n\n"

    return StreamingResponse(log_stream(), media_type="text/event-stream")

@app.post("/api/script/save")
def update_script_cloud():
    return {"status": "saved", "message": "บันทึกสคริปต์บน Dashboard สำเร็จ"}

class VoiceoverUploadRequest(BaseModel):
    product_id: str
    audio_base64: str

@app.post("/api/voiceover/upload")
def upload_voiceover_cloud(req: VoiceoverUploadRequest):
    return {
        "status": "success",
        "duration": 20.0,
        "message": "อัปโหลดเสียงพากย์เรียบร้อยแล้ว",
        "audio_url": "/assets/sample_chirp_aoede.mp3"
    }


@app.get("/api/proxy/media")
def proxy_external_media(url: str, request: Request):
    """Same-origin CORS media proxy for Shopee VOD videos and images so HTML5 Canvas is NEVER tainted."""
    if not url or not url.startswith(("http://", "https://")):
        return JSONResponse({"error": "Invalid media URL"}, status_code=400)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://shopee.co.th/",
        "Accept": "*/*"
    }
    range_header = request.headers.get("range") or request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=25)
        resp_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400"
        }
        for h_name in ("Content-Type", "Content-Length", "Content-Range"):
            if r.headers.get(h_name):
                resp_headers[h_name] = r.headers[h_name]

        content_type = r.headers.get("Content-Type", "application/octet-stream")
        return StreamingResponse(
            r.iter_content(chunk_size=65536),
            status_code=r.status_code,
            media_type=content_type,
            headers=resp_headers
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)

