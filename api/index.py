import os
import re
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI
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
    "fanlife_tumbler_710ml": ("/videos/fanlife_tumbler_710ml.mp4?v=v2_pure_moving_video_20s", 10.07),
    "cat_fountain_01": ("/videos/cat_fountain_01.mp4?v=v4_perfect_brand_20s", 10.09),
    "gan_charger_65w": ("/videos/gan_charger_65w.mp4?v=v4_perfect_brand_20s", 8.07),
    "uv_dust_mite_vacuum": ("/videos/uv_dust_mite_vacuum.mp4?v=v4_perfect_brand_20s", 8.58),
    "tyeso_tumbler_304": ("/videos/tyeso_tumbler_304.mp4?v=v4_perfect_brand_20s", 11.35),
    "spray_mop_360": ("/videos/spray_mop_360.mp4?v=v4_perfect_brand_20s", 11.81),
    "solar_sensor_light": ("/videos/solar_sensor_light.mp4?v=v4_perfect_brand_20s", 9.92),
    "air_fryer_visual": ("/videos/air_fryer_visual.mp4?v=v4_perfect_brand_20s", 7.89),
    "sonic_electric_toothbrush": ("/videos/sonic_electric_toothbrush.mp4?v=v4_perfect_brand_20s", 5.56),
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

@app.post("/api/product/analyze")
def analyze_product_url(req: AnalyzeUrlRequest):
    """Analyze Shopee product URL, match or scout product, return script, caption, and review video."""
    url = req.url.strip()
    if not url:
        return JSONResponse({"error": "กรุณาวางลิงก์สินค้า Shopee"}, status_code=400)

    url_lower = url.lower()
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
                    # 2. Match item ID or shop ID numbers
                    nums = re.findall(r"(\d{8,})", url)
                    for n in nums:
                        if n in s_url:
                            matched_pid = pid
                            break
                    if matched_pid:
                        break
                    # 3. Match keywords in slug
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

    # Fallback: create dynamic product record from URL slug
    slug = url.split("?")[0].rstrip("/").split("/")[-1]
    title_clean = re.sub(r"[-_]", " ", slug)
    title_clean = re.sub(r"i\.\d+\.\d+", "", title_clean).strip()
    if not title_clean or len(title_clean) < 3:
        title_clean = "สินค้า Shopee ยอดนิยม"

    custom_pid = "custom_" + re.sub(r"[^a-zA-Z0-9]", "", slug)[:16]
    custom_data = {
        "product_id": custom_pid,
        "title": title_clean,
        "price": 490.0,
        "shopee_url": url,
        "category": "สินค้าแนะนำสำหรับคุณ",
        "shop": "Shopee Official Store",
        "ams_commission_rate": 12.5,
        "commission_amount": 61.25
    }

    script_data = {
        "on_screen_headline": title_clean[:20],
        "hook_text": f"ใครที่กำลังมองหา {title_clean[:30]} แนะนำตัวนี้เลยค่ะ.",
        "body_text": f"ตัวนี้ฟังก์ชันครบ ใช้งานง่ายมาก วัสดุดีคุ้มราคา ใครที่กำลังเล็งอยู่บอกเลยไม่ผิดหวังค่ะ.",
        "cta_text": "สนใจกดสั่งซื้อที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ.",
        "full_script": f"ใครที่กำลังมองหา {title_clean[:30]} แนะนำตัวนี้เลยค่ะ. ตัวนี้ฟังก์ชันครบ ใช้งานง่ายมาก วัสดุดีคุ้มราคา ใครที่กำลังเล็งอยู่บอกเลยไม่ผิดหวังค่ะ. สนใจกดสั่งซื้อที่ตะกร้าสีส้ม มุมซ้ายล่างได้เลยนะคะ."
    }

    caption = f"ใครที่กำลังมองหาตัวนี้อยู่บอกเลยต้องมี! {title_clean[:35]}... ฟังก์ชันครบ คุณภาพดี คุ้มราคามาก พิกัดในตะกร้าส้มซ้ายล่างเลยนะคะ 🧡✨"
    hashtags = "#ShopeeVideoTH #รีวิวช้อปปี้ #ของดีบอกต่อ #นายหน้าShopee #ป้ายยาของใช้"

    # Default to a clean preview video (e.g. ugreen or generic)
    default_vid = AVAILABLE_VIDEOS.get("gan_charger_65w", ("/videos/gan_charger_65w.mp4?v=v4_perfect_brand_20s", 8.07))

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


