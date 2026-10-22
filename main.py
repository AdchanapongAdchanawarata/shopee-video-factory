import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# โหลดค่า Environment Variables และ API Key
load_dotenv()

# Add root folder to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Import pipeline modules cleanly
from modules import (
    scout_shopee_products,
    curate_product_videos,
    generate_shopee_script,
    generate_voiceover_and_subtitles,
    assemble_curated_video,
)

BANNER = r"""
========================================================================
 🛍️  SHOPEE AI AFFILIATE HYBRID VIDEO FACTORY (THAILAND MARKET)  🛍️
========================================================================
 * Anti-Spam Standard: 103% Zoom, Color-Graded, Rapid Cuts (1.8s)
 * Strict Commission: Only Extra Commission / AMS (>= 8%)
 * Audio & Captions: Thai TTS (+15% speed) + Safe-Zone ASS Subtitles
========================================================================
"""

def main():
    parser = argparse.ArgumentParser(description="Shopee AI Affiliate Video Factory")
    parser.add_argument("--product_id", type=str, default="cat_fountain_01", help="รหัสหรือ URL สินค้า Shopee ที่ต้องการทำคลิป")
    parser.add_argument("--product_name", type=str, default="น้ำพุแมวไร้สายเซนเซอร์อัตโนมัติ 3.2L สแตนเลส 304", help="ชื่อสินค้าสำหรับให้ AI เขียนสคริปต์")
    parser.add_argument("--url", type=str, default=None, help="Shopee Product URL (สำหรับดึงข้อมูลสดผ่าน Playwright)")
    parser.add_argument("--step", type=str, default="all", choices=["all", "1", "1.5", "2", "3", "4"], help="เลือกขั้นตอนที่ต้องการรัน")
    parser.add_argument("--mock", action="store_true", help="รันด้วยข้อมูลตัวอย่าง (Offline / Test Mode)")
    parser.add_argument("--duration", type=float, default=20.0, help="ความยาววิดีโอเป้าหมาย (วินาที เช่น 20.0)")
    args = parser.parse_args()

    print(BANNER)
    product_id = args.product_id
    product_name = args.product_name
    use_mock = args.mock or (not args.url and not config.GEMINI_API_KEY)

    print(f"🚀 เริ่มต้นกระบวนการสร้างคลิปอัตโนมัติสำหรับสินค้า: {product_name} (ID: {product_id})")
    if use_mock:
        print("💡 โหมดทดสอบ (Test/Mock Mode): ใช้งานเทมเพลตและข้อมูลในเครื่อง")

    # ขั้นตอนที่ 1: ค้นหาและคัดกรองสินค้า + ตรวจสอบคอมมิชชั่น AMS >= 8%
    if args.step in ("all", "1"):
        print("\n[Step 1] กำลังดึงข้อมูลสินค้า รีวิว 5 ดาว/1 ดาว และตรวจเช็ค AMS Commission (>= 8%)...")
        product_data = scout_shopee_products(product_id, url=args.url, use_mock=use_mock)
        print(f"✅ ข้อมูลสินค้า: {product_data.get('title')} | คอมมิชชั่น AMS: {product_data.get('ams_commission_rate')}%")

    # ขั้นตอนที่ 1.5: สแกนและคัดเลือกช็อตวิดีโอรีวิวด้วย AI Vision
    if args.step in ("all", "1.5"):
        print("\n[Step 1.5] กำลังสแกนคัดช็อตสวยด้วย OpenCV (เบลอ/มืด) + Gemini Vision...")
        curated_segments = curate_product_videos(product_id, product_name, use_mock=use_mock)
        print(f"🎥 คัดเลือกช็อตเด็ดได้ทั้งหมด {len(curated_segments)} ช็อต")

    # ขั้นตอนที่ 2: เขียนสคริปต์ป้ายยาจากรีวิวจริง
    script_data = None
    if args.step in ("all", "2"):
        print("\n[Step 2] กำลังวิเคราะห์อินไซต์รีวิวและเขียนสคริปต์ 20 วินาที...")
        script_data = generate_shopee_script(product_id, product_name, use_mock=use_mock)
        print(f"✍️ ได้สคริปต์ Hook (0-3s): {script_data.get('hook_text')}")
        print(f"📝 ความยาวสคริปต์รวม: {len(script_data.get('full_script', '').split())} คำ")

    # ขั้นตอนที่ 3: สร้างเสียงพากย์ไทยและไฟล์ซับไตเติล
    if args.step in ("all", "3"):
        if not script_data:
            import json
            s_file = config.OUTPUT_DIR / product_id / "script.json"
            if s_file.is_file():
                with open(s_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
            else:
                script_data = generate_shopee_script(product_id, product_name, use_mock=use_mock)

        print("\n[Step 3] กำลังสังเคราะห์เสียงพากย์ไทยและสร้างซับไตเติลภาษาไทย (.ass)...")
        sub_meta = generate_voiceover_and_subtitles(product_id, script_data)
        print(f"🎙️ สร้างเสียงพากย์เสร็จแล้ว: ความยาว {sub_meta['duration']:.2f} วินาที")

    # ขั้นตอนที่ 4: ประกอบร่างวิดีโอด้วย FFmpeg (Hybrid Assembly)
    if args.step in ("all", "4"):
        print("\n[Step 4] กำลังตัดต่อและประกอบร่างวิดีโอ (ซูม 103%, ล้าง Metadata, มิกซ์ BGM 10%, ฝังซับ)...")
        final_video_path = assemble_curated_video(product_id, target_duration=args.duration)
        print(f"\n🎉 สำเร็จเรียบร้อย! ไฟล์วิดีโอพร้อมโพสต์อยู่ที่: {final_video_path}")

if __name__ == "__main__":
    main()
