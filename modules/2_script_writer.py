import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

class ShopeeScriptResult(BaseModel):
    pain_point_identified: str = Field(description="ปัญหาหรือความกังวลหลักของลูกค้าจากรีวิว (เช่น แมวไม่ยอมกินน้ำ, กลัวสายไฟช็อต, พลาสติกเกิดเมือก)")
    praised_feature_identified: str = Field(description="จุดเด่นที่ลูกค้าชมมากที่สุด (เช่น ไร้สาย ปลอดภัย สแตนเลสแท้ เสียงเงียบกริบ)")
    on_screen_headline: str = Field(description="ข้อความพาดหัวตัวใหญ่บนหน้าจอช่วง 0-3 วินาทีแรก (สั้น กระชับ ดึงดูด ไม่เกิน 5-7 คำ)")
    hook_text: str = Field(description="บทพูดทักทายเปิดคลิป 0-3 วินาที จี้จุดเจ็บหรือเปิดประเด็นชวนสงสัย (ประมาณ 8-12 คำ)")
    body_text: str = Field(description="บทพูดเนื้อหา 3-15 วินาที อธิบายวิธีแก้ปัญหา โชว์จุดเด่นและเหตุผลที่ต้องมี (ประมาณ 25-35 คำ)")
    cta_text: str = Field(description="บทพูดปิดท้าย 15-20 วินาที กระตุ้นให้รีบกดตะกร้าส้ม พร้อมบอกสิทธิพิเศษ (ประมาณ 10-15 คำ)")
    visual_broll_prompts: List[str] = Field(description="คำแนะนำภาพ B-roll หรือฉากที่ควรแสดงคู่กับแต่ละท่อนบทพูด (3-5 ฉาก)")
    full_script: str = Field(description="บทพูดทั้งหมดรวมกัน เรียงต่อกันเป็นธรรมชาติ ความยาวรวม 45-60 คำ")

def build_script_prompt(product_title: str, price: float, reviews_5_star: List[str], reviews_1_star: List[str]) -> str:
    combined_5_star = "\n- ".join(reviews_5_star[:10]) if reviews_5_star else "สินค้าคุณภาพดี ใช้งานง่าย แมวชอบมาก"
    combined_1_star = "\n- ".join(reviews_1_star[:5]) if reviews_1_star else "กลัวสายไฟเกะกะ กลัวล้างยาก"

    prompt = f"""
คุณคือนักเขียนสคริปต์คลิปขายของ Shopee Video & TikTok มืออาชีพ สาย "ป้ายยา" ที่ทำยอดขายถล่มทลายในตลาดไทย
จงวิเคราะห์ข้อมูลสินค้าและรีวิวจากผู้ใช้จริงด้านล่างนี้:

[ข้อมูลสินค้า]
- ชื่อสินค้า: {product_title}
- ราคา: {price:.2f} บาท

[รีวิว 5 ดาว (จุดที่ลูกค้าชอบและชมมากที่สุด)]:
- {combined_5_star}

[รีวิว 1 ดาว / ข้อกังวล (จุดเจ็บหรือความลังเลของลูกค้า)]:
- {combined_1_star}

[เป้าหมายและข้อกำหนดสคริปต์ (CRITICAL CONSTRAINTS)]:
1. สไตล์: พูดภาษาไทยสำเนียงเพื่อนสาวป้ายยา เป็นกันเอง กระฉับกระเฉง จังหวะเร็ว ไม่ใช้ศัพท์ทางการ
2. โครงสร้าง:
   - Hook (0-3s): เปิดด้วยปัญหาหรือคำถามสะกิดใจทันที ห้ามเกริ่นสวัสดี ห้ามมีโลโก้
   - Body (3-15s): คลายกังวล นำเสนอทางแก้ ชูจุดเด่นที่ลูกค้า 5 ดาวการันตี
   - CTA (15-20s): สั่งให้กดตะกร้าส้มซ้ายมือด่วน ย้ำว่ากำลังมีโปรหรือของใกล้หมด
3. ความยาว: สคริปต์รวม (full_script) ต้องมีความยาวอย่างเคร่งครัดที่ 45 - 60 คำภาษาไทย (พูดด้วยความเร็ว +15% จะได้เวลาประมาณ 18-22 วินาที พอดีเป๊ะ)
4. On-Screen Headline: ต้องเป็นข้อความสั้นๆ ติดหู เช่น "หยุดใช้แบบมีสาย!", "แมวใครไม่กินน้ำ ต้องดู!"
"""
    return prompt

def generate_mock_script(product_id: str, product_title: str, price: float) -> ShopeeScriptResult:
    """Generate high-converting fallback script for offline testing or without API key."""
    # Check if tailored data exists in products_db.json
    db_item = None
    if config.PRODUCTS_DB_PATH.is_file():
        try:
            with open(config.PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                db = json.load(f)
                db_item = db.get(product_id)
        except Exception:
            pass

    if db_item:
        headline = db_item.get("headline", f"ของดีบอกต่อ! {product_title[:20]}")
        hook = db_item.get("hook_idea", "ใครกำลังมองหาของดีราคาคุ้มค่า ฟังทางนี้ด่วนเลยค่ะ!")
        rev = db_item.get("reviews_5_star", ["คุณภาพดีมาก คุ้มค่าคุ้มราคา"])[0]
        body = f"ตัวนี้เป็น {db_item.get('title', product_title)} {rev} ใช้งานง่าย คุ้มค่ามากเลยค่ะ"
        cta = "รีบกดสั่งที่ตะกร้าสีส้มซ้ายมือด่วนเลย ตอนนี้มีโค้ดลดเพิ่มด้วยนะคะ!"
        full = f"{hook} {body} {cta}"
        return ShopeeScriptResult(
            pain_point_identified=db_item.get("reviews_1_star", ["ของเดิมใช้งานไม่สะดวก"])[0] if db_item.get("reviews_1_star") else "ของเดิมมีปัญหา",
            praised_feature_identified=rev,
            on_screen_headline=headline,
            hook_text=hook,
            body_text=body,
            cta_text=cta,
            visual_broll_prompts=[
                f"ช็อตทดสอบการใช้งานจริง {product_title[:25]}",
                "ภาพโคลสอัพดีเทลสินค้าชัดเจน คุณภาพเกรดพรีเมียม",
                "ช็อตนิ้วชี้ไปที่มุมซ้ายล่างพร้อมโปรโมชั่น"
            ],
            full_script=full
        )

    return ShopeeScriptResult(
        pain_point_identified="แมวไม่ยอมกินน้ำ เสี่ยงโรคไต และน้ำพุแบบเก่ามีสายไฟเกะกะแถมกลัวไฟดูด",
        praised_feature_identified="ระบบไร้สาย แบตทน สแตนเลส 304 เสียงเงียบสนิท แมวชอบกินน้ำเยอะขึ้น",
        on_screen_headline="ทาสแมวต้องดู! น้ำพุไร้สายตัวจบ",
        hook_text="ใครที่น้องแมวดื่มน้ำน้อย หรือกลัวเรื่องสายไฟช็อต ฟังทางนี้ด่วนเลยค่ะ!",
        body_text="ตัวนี้เป็นน้ำพุแมวไร้สาย สแตนเลส 304 แท้ เซนเซอร์อัจฉริยะเดินผ่านน้ำถึงไหล เสียงเงียบกริบ แบตอึดเป็นเดือน ล้างง่ายไม่เป็นเมือกเลยค่ะ",
        cta_text="รีบกดที่ตะกร้าสีส้มซ้ายมือด่วนเลย ตอนนี้มีโค้ดลดเพิ่มด้วยนะคะ!",
        visual_broll_prompts=[
            "ภาพแมวเดินเข้ามาใกล้แล้วน้ำพุเริ่มไหลอัตโนมัติ (Hook Action)",
            "ภาพโคลสอัพตัวถังสแตนเลส 304 สะอาดเงาวับ ถอดล้างง่าย",
            "ภาพแมวกำลังเลียน้ำอย่างมีความสุข เสียงน้ำไหลเบาๆ",
            "ช็อตนิ้วชี้ไปที่มุมซ้ายล่างพร้อมข้อความโปรโมชั่น"
        ],
        full_script="ใครที่น้องแมวดื่มน้ำน้อย หรือกลัวเรื่องสายไฟช็อต ฟังทางนี้ด่วนเลยค่ะ! ตัวนี้เป็นน้ำพุแมวไร้สาย สแตนเลส 304 แท้ เซนเซอร์อัจฉริยะเดินผ่านน้ำถึงไหล เสียงเงียบกริบ แบตอึดเป็นเดือน ล้างง่ายไม่เป็นเมือกเลยค่ะ รีบกดที่ตะกร้าสีส้มซ้ายมือด่วนเลย ตอนนี้มีโค้ดลดเพิ่มด้วยนะคะ!"
    )

def generate_shopee_script(product_id: str, product_name: str, use_mock: bool = False) -> Dict[str, Any]:
    """
    Main entry point for Module 2:
    Takes product reviews, analyzes customer psychology, and creates 20s Hook-Body-CTA script.
    """
    out_dir = config.OUTPUT_DIR / product_id
    out_dir.mkdir(parents=True, exist_ok=True)
    script_output_file = out_dir / "script.json"

    # Load product data from module 1 if available
    product_data_file = out_dir / "product_data.json"
    price = 490.0
    reviews_5 = []
    reviews_1 = []

    if product_data_file.is_file():
        try:
            with open(product_data_file, "r", encoding="utf-8") as f:
                pdata = json.load(f)
                price = pdata.get("price", price)
                reviews_5 = pdata.get("reviews_5_star", [])
                reviews_1 = pdata.get("reviews_1_star", [])
                if not product_name:
                    product_name = pdata.get("title", product_name)
        except Exception as e:
            print(f"⚠️ Could not read {product_data_file}: {e}")

    api_key = config.GEMINI_API_KEY
    if not api_key or use_mock:
        print("ℹ️ Running script generator with curated Thai 'ป้ายยา' template (mock/offline mode)")
        result_obj = generate_mock_script(product_id, product_name, price)
    else:
        print(f"🧠 Calling Gemini 2.5 Flash to analyze Thai buyer psychology for: {product_name}...")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = build_script_prompt(product_name, price, reviews_5, reviews_1)

            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ShopeeScriptResult,
                    temperature=0.7,
                ),
            )
            result_obj = ShopeeScriptResult.model_validate_json(response.text)
        except Exception as e:
            print(f"⚠️ Gemini API failed ({e}). Falling back to optimized template.")
            result_obj = generate_mock_script(product_id, product_name, price)

    result_dict = result_obj.model_dump()
    with open(script_output_file, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    print(f"✅ Generated Script saved to: {script_output_file}")
    print(f"🎯 Headline: {result_dict['on_screen_headline']}")
    print(f"🪝 Hook: {result_dict['hook_text']}")
    print(f"📦 Word Count: {len(result_dict['full_script'].split())} words")
    return result_dict

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Thai Review Script Writer")
    parser.add_argument("--product_id", type=str, default="cat_fountain_01")
    parser.add_argument("--product_name", type=str, default="น้ำพุแมวไร้สายเซนเซอร์อัตโนมัติ")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    generate_shopee_script(args.product_id, args.product_name, use_mock=args.mock)
