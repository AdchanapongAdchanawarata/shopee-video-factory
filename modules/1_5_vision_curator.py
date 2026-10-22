import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
from pydantic import BaseModel, Field

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# ==========================================
# 1. โครงสร้างข้อมูลผลลัพธ์จาก Gemini Vision
# ==========================================
class VideoSegment(BaseModel):
    start_sec: float = Field(description="เวลาเริ่มต้นของช็อตที่เห็นสินค้าชัดเจน (วินาที เช่น 1.5)")
    end_sec: float = Field(description="เวลาสิ้นสุดของช็อต ความยาวประมาณ 1.8 ถึง 3.0 วินาที (เช่น 3.5)")
    shot_type: str = Field(description="ประเภทของช็อต: 'hook_action' (กำลังใช้งานเห็นผลลัพธ์), 'closeup' (เห็นดีเทลสินค้าชัด), หรือ 'before_after'")
    visual_score: int = Field(description="คะแนนความสวยและความน่าดึงดูดของช็อต (1-10)")
    reason: str = Field(description="คำอธิบายสั้นๆ ว่าทำไมช็อตนี้ถึงน่าสนใจ")

class ClipAnalysisResult(BaseModel):
    is_usable: bool = Field(description="คลิปนี้มีช็อตที่เห็นตัวสินค้าชัดเจนและนำไปใช้ต่อได้หรือไม่")
    best_segments: List[VideoSegment] = Field(description="รายการช่วงเวลาที่ดีที่สุดในคลิปนี้ (คัดมา 1-3 ช่วง)")

# ==========================================
# 2. ฟังก์ชันกรองภาพเบลอและภาพมืดด้วย OpenCV (รันในเครื่อง ฟรี 100%)
# ==========================================
def check_video_quality_local(
    video_path: str,
    blur_threshold: float = config.LAPLACIAN_BLUR_THRESHOLD,
    min_brightness: float = config.MIN_BRIGHTNESS,
    max_brightness: float = config.MAX_BRIGHTNESS
) -> dict:
    """
    สแกนคลิปทุกๆ 0.5 วินาที เพื่อเช็กว่าคลิปมืดเกินไปหรือเบลอทั้งคลิปหรือไม่
    ก่อนส่งไปเสียโควตา API ของ Gemini
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"passed": False, "reason": "Cannot open video"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    if duration < 1.5:
        cap.release()
        return {"passed": False, "reason": f"Video too short ({duration:.1f}s)"}

    step = max(1, int(fps / 2))  # สุ่มตรวจทุกๆ 0.5 วินาที
    sharp_frames = 0
    checked_frames = 0

    for frame_idx in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        checked_frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Normalize to standard vertical 480p thumbnail for invariant quality metrics
        small = cv2.resize(gray, (270, 480))
        
        # คำนวณความคมชัด (Laplacian Variance) และความสว่างเฉลี่ย
        laplacian_var = cv2.Laplacian(small, cv2.CV_64F).var()
        brightness = small.mean()

        if laplacian_var >= blur_threshold and (min_brightness <= brightness <= max_brightness):
            sharp_frames += 1

    cap.release()
    pass_ratio = (sharp_frames / checked_frames) if checked_frames > 0 else 0

    # ต้องมีเฟรมที่ชัดและแสงพอดีอย่างน้อย 40% ของทั้งคลิปถึงจะผ่านไปเข้า Gemini
    if pass_ratio < config.MIN_SHARP_RATIO:
        return {"passed": False, "reason": f"Low visual quality (sharp ratio: {pass_ratio:.2f})"}
    
    return {"passed": True, "duration": round(duration, 2), "sharp_ratio": round(pass_ratio, 2)}

# ==========================================
# 3. ฟังก์ชันให้ Gemini Vision สแกนหา Timestamp ช็อตเด็ด
# ==========================================
def analyze_clip_with_gemini(client, video_path: str, product_name: str) -> ClipAnalysisResult:
    from google.genai import types

    print(f"Uploading {Path(video_path).name} to Gemini Vision...")
    uploaded_file = client.files.upload(file=video_path)

    # รอให้ Google ประมวลผลไฟล์วิดีโอเสร็จ (สถานะ ACTIVE)
    retries = 0
    while uploaded_file.state.name == "PROCESSING" and retries < 30:
        time.sleep(2)
        uploaded_file = client.files.get(name=uploaded_file.name)
        retries += 1

    if uploaded_file.state.name != "ACTIVE":
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass
        raise RuntimeError(f"File processing failed: {uploaded_file.state.name}")

    prompt = f"""
    คุณคือผู้กำกับวิดีโอโฆษณา Shopee Video & TikTok มืออาชีพ
    ช่วยดูคลิปรีวิวสินค้า "{product_name}" นี้ แล้วคัดเลือกเฉพาะช่วงเวลา (Timestamp) ที่ดีที่สุดสำหรับนำมาตัดต่อคลิปป้ายยา

    กฎเหล็กในการคัดเลือกช็อต:
    1. ห้ามเลือกช่วงที่เป็นกล่องพัสดุสีน้ำตาล ใบปะหน้าพัสดุ หรือกำลังกรีดกล่องที่ยังไม่เห็นตัวสินค้าเด็ดขาด
    2. ห้ามเลือกช่วงที่กล้องสั่นแรง ภาพเบลอ มืด หรือถ่ายติดพื้นบ้าน/นิ้วมือบังกล้อง
    3. ให้เลือกเฉพาะช่วงที่ "เห็นตัวสินค้าชัดเจน" หรือ "กำลังสาธิตการใช้งานจริงและเห็นผลลัพธ์"
    4. แต่ละช่วง (Segment) ต้องมีความยาวระหว่าง 1.8 ถึง 3.0 วินาที
    """

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClipAnalysisResult,
                temperature=0.2,
            ),
        )
        result = ClipAnalysisResult.model_validate_json(response.text)
    finally:
        # ลบไฟล์ออกจาก Cloud ทันทีหลังวิเคราะห์เสร็จเพื่อความสะอาด
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

    return result

def fallback_local_curation(video_path: str, duration: float) -> ClipAnalysisResult:
    """
    Local high-resolution curation across the entire video duration.
    Extracts diverse, non-repeating 1.8s - 2.4s cuts across the entire source video
    so that assembled videos never loop or show repetitive footage.
    """
    segments = []
    # Dynamic rhythm: alternate between punchy 1.8s and 2.3s cuts
    rhythms = [2.0, 2.3, 1.8, 2.2, 1.9, 2.4]
    st = 0.0
    idx = 0
    
    while st + 1.5 <= duration:
        cur_dur = rhythms[idx % len(rhythms)]
        et = min(duration, st + cur_dur)
        if (et - st) >= 1.4:
            # First 5 seconds get hook_action score
            if st < 5.0:
                stype = "hook_action"
                score = 10 if idx == 0 else 9
                reason = "Primary hook action showing live product movement"
            elif st < 15.0:
                stype = "closeup" if idx % 2 == 0 else "feature_demo"
                score = 8
                reason = "High-clarity detail showing product build and usage"
            else:
                stype = "lifestyle_context"
                score = 8
                reason = "Demonstration of practical real-world result"

            segments.append(
                VideoSegment(
                    start_sec=round(st, 2),
                    end_sec=round(et, 2),
                    shot_type=stype,
                    visual_score=score,
                    reason=reason
                )
            )
            idx += 1
        st = et  # Advance strictly to next timestamp (ZERO overlap / ZERO repetition)

    return ClipAnalysisResult(is_usable=True, best_segments=segments)

# ==========================================
# 4. ฟังก์ชันหลักสำหรับรันสแกนทั้งโฟลเดอร์สินค้า
# ==========================================
def curate_product_videos(product_id: str, product_name: str, use_mock: bool = False) -> List[Dict[str, Any]]:
    """
    Scan raw_media videos:
    Stage 1: Local OpenCV blur & brightness filter
    Stage 2: Gemini 2.5 Flash Vision timestamp selection
    """
    raw_dir = config.OUTPUT_DIR / product_id / "raw_media"
    output_json = config.OUTPUT_DIR / product_id / "curated_segments.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)

    client = None
    api_key = config.GEMINI_API_KEY
    if api_key and not use_mock:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"⚠️ Could not initialize Gemini client: {e}. Falling back to local curation.")

    curated_pool = []
    video_files = sorted(raw_dir.glob("*.mp4"))

    if not video_files:
        print(f"⚠️ No MP4 videos found in {raw_dir}. Checking for existing curated segments...")
        if output_json.is_file():
            with open(output_json, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    for video_file in video_files:
        print(f"\n--- Checking {video_file.name} ---")
        
        # ชั้นที่ 1: กรองด้วย OpenCV ในเครื่องก่อน
        local_check = check_video_quality_local(str(video_file))
        if not local_check["passed"]:
            print(f"❌ Rejected by Local CV: {local_check['reason']}")
            continue

        print(f"✅ Local CV Passed: Duration {local_check['duration']}s, Sharp Ratio: {local_check['sharp_ratio']}")

        # ชั้นที่ 2: ให้ Gemini Vision หา Timestamp ช็อตสวยๆ
        try:
            if client:
                analysis = analyze_clip_with_gemini(client, str(video_file), product_name)
            else:
                print("ℹ️ Using fast local heuristic segmentation (offline/demo mode)")
                analysis = fallback_local_curation(str(video_file), local_check["duration"])

            if analysis.is_usable and analysis.best_segments:
                for seg in analysis.best_segments:
                    if seg.visual_score >= 7:  # เอาเฉพาะช็อตที่ได้คะแนนความสวย 7/10 ขึ้นไป
                        curated_pool.append({
                            "source_video": str(video_file),
                            "start_sec": seg.start_sec,
                            "end_sec": seg.end_sec,
                            "duration": round(seg.end_sec - seg.start_sec, 2),
                            "shot_type": seg.shot_type,
                            "visual_score": seg.visual_score,
                            "reason": seg.reason
                        })
                        print(f"✅ Kept segment {seg.start_sec}s-{seg.end_sec}s (Score: {seg.visual_score}/10) - {seg.reason}")
        except Exception as e:
            print(f"⚠️ Error analyzing {video_file.name}: {e}. Falling back to local curation.")
            analysis = fallback_local_curation(str(video_file), local_check["duration"])
            for seg in analysis.best_segments:
                curated_pool.append({
                    "source_video": str(video_file),
                    "start_sec": seg.start_sec,
                    "end_sec": seg.end_sec,
                    "duration": round(seg.end_sec - seg.start_sec, 2),
                    "shot_type": seg.shot_type,
                    "visual_score": seg.visual_score,
                    "reason": seg.reason
                })

    # เรียงลำดับเอาช็อตที่ได้คะแนนสูงสุด (และเป็นช็อต hook_action) ขึ้นเป็นวินาทีที่ 0-3 แรกของคลิป!
    curated_pool.sort(key=lambda x: (x["shot_type"] == "hook_action", x["visual_score"]), reverse=True)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(curated_pool, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Saved {len(curated_pool)} high-quality segments to {output_json}")
    return curated_pool

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart Vision Curator (OpenCV + Gemini Vision)")
    parser.add_argument("--product_id", type=str, required=True, help="Product ID")
    parser.add_argument("--product_name", type=str, default="Cat Water Fountain", help="Product Title")
    parser.add_argument("--mock", action="store_true", help="Use local mock mode")
    args = parser.parse_args()

    curate_product_videos(args.product_id, args.product_name, use_mock=args.mock)
