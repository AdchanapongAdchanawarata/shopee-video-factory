import os
import sys
import json
import base64
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from modules import (
    scout_shopee_products,
    curate_product_videos,
    generate_shopee_script,
    generate_voiceover_and_subtitles,
    assemble_curated_video,
)

app = FastAPI(
    title="Shopee AI Affiliate Video Factory",
    description="Local-first automated pipeline for Shopee Video & TikTok Thailand Affiliate",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs and static assets
app.mount("/output", StaticFiles(directory=str(config.OUTPUT_DIR)), name="output")
app.mount("/assets", StaticFiles(directory=str(config.ASSETS_DIR)), name="assets")

# Global in-memory log bus for SSE streaming
JOB_LOGS: Dict[str, List[str]] = {}
ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}

class PipelineRunRequest(BaseModel):
    product_id: str = "cat_fountain_01"
    product_name: str = "น้ำพุแมวไร้สายเซนเซอร์อัตโนมัติ 3.2L สแตนเลส 304"
    url: Optional[str] = None
    step: str = "all"
    mock: bool = False
    duration: float = 20.0
    voice_engine: str = "neural2"

class ScriptUpdateRequest(BaseModel):
    product_id: str
    on_screen_headline: str
    hook_text: str
    body_text: str
    cta_text: str
    full_script: str

def emit_log(job_id: str, message: str):
    """Append log to job buffer."""
    if job_id not in JOB_LOGS:
        JOB_LOGS[job_id] = []
    JOB_LOGS[job_id].append(message)
    print(f"[{job_id[:8]}] {message}")

def run_pipeline_worker(job_id: str, req: PipelineRunRequest):
    """Background worker executing pipeline steps."""
    ACTIVE_JOBS[job_id] = {"status": "running", "step": req.step, "progress": 5}
    pid = req.product_id
    pname = req.product_name
    use_mock = req.mock or (not req.url and not config.GEMINI_API_KEY)

    try:
        emit_log(job_id, f"🚀 เริ่มต้นการสร้างวิดีโอสำหรับ: {pname} (ID: {pid})")
        if use_mock:
            emit_log(job_id, "💡 ใช้งานโหมดทดสอบ (Test/Mock Mode)")

        # STEP 1
        if req.step in ("all", "1"):
            ACTIVE_JOBS[job_id]["step_label"] = "Step 1: Product Scout & AMS Gate"
            ACTIVE_JOBS[job_id]["progress"] = 20
            emit_log(job_id, "\n[Step 1] กำลังดึงข้อมูลสินค้า รีวิว และตรวจสอบค่าคอมมิชชั่น AMS (>= 8%)...")
            p_data = scout_shopee_products(pid, url=req.url, use_mock=use_mock)
            if p_data.get("title"):
                pname = p_data["title"]
            emit_log(job_id, f"✅ ดึงข้อมูลสำเร็จ: {pname} | คอมมิชชั่น AMS = {p_data.get('ams_commission_rate')}% (เกณฑ์ขั้นต่ำ {config.MIN_AMS_COMMISSION_RATE}%)")
        else:
            p_file = config.OUTPUT_DIR / pid / "product_data.json"
            if p_file.is_file():
                try:
                    with open(p_file, "r", encoding="utf-8") as pf:
                        p_data = json.load(pf)
                        if p_data.get("title"):
                            pname = p_data["title"]
                except Exception:
                    pass

        # STEP 1.5
        if req.step in ("all", "1.5"):
            ACTIVE_JOBS[job_id]["step_label"] = "Step 1.5: Smart Vision Curator"
            ACTIVE_JOBS[job_id]["progress"] = 40
            emit_log(job_id, "\n[Step 1.5] กรองวิดีโอรีวิวด้วย OpenCV (เบลอ/มืด) + Gemini Vision คัดช็อตเด็ด...")
            curated = curate_product_videos(pid, pname, use_mock=use_mock)
            emit_log(job_id, f"🎥 คัดเลือกช็อตคุณภาพสูง (Hook Action / Closeup) ได้ทั้งหมด {len(curated)} ช็อต")

        # STEP 2
        script_data = None
        if req.step in ("all", "2"):
            ACTIVE_JOBS[job_id]["step_label"] = "Step 2: Script Writer"
            ACTIVE_JOBS[job_id]["progress"] = 60
            emit_log(job_id, "\n[Step 2] Gemini 2.5 Flash กำลังวิเคราะห์อินไซต์รีวิวและเขียนสคริปต์ป้ายยา 20 วินาที...")
            script_data = generate_shopee_script(pid, pname, use_mock=use_mock)
            emit_log(job_id, f"✍️ Hook (0-3s): {script_data.get('hook_text')}")
            emit_log(job_id, f"🎯 Headline: {script_data.get('on_screen_headline')}")

        # STEP 3
        if req.step in ("all", "3"):
            ACTIVE_JOBS[job_id]["step_label"] = "Step 3: Voice & Subtitles"
            ACTIVE_JOBS[job_id]["progress"] = 80
            emit_log(job_id, f"\n[Step 3] กำลังจัดการเสียงพากย์ ({req.voice_engine}) และสร้างซับไตเติลภาษาไทย (.ass)...")
            if not script_data:
                s_file = config.OUTPUT_DIR / pid / "script.json"
                if s_file.is_file():
                    with open(s_file, "r", encoding="utf-8") as f:
                        script_data = json.load(f)
                else:
                    script_data = generate_shopee_script(pid, pname, use_mock=use_mock)
            sub_meta = generate_voiceover_and_subtitles(pid, script_data, voice_choice=req.voice_engine)
            emit_log(job_id, f"🎙️ สร้างเสียงพากย์เสร็จสิ้น: ความยาว {sub_meta['duration']:.2f} วินาที (เว้นระยะขอบล่าง 25% ไม่บังตะกร้าส้ม)")

        # STEP 4
        if req.step in ("all", "4"):
            ACTIVE_JOBS[job_id]["step_label"] = "Step 4: Video Assembler"
            ACTIVE_JOBS[job_id]["progress"] = 95
            emit_log(job_id, "\n[Step 4] FFmpeg กำลังตัดต่อสลับช็อต 1.8s, ซูม 103%, มิกซ์เพลง 10% และฝังซับไตเติล...")
            final_mp4 = assemble_curated_video(pid, target_duration=req.duration)
            emit_log(job_id, f"\n🎉 สำเร็จเรียบร้อย! วิดีโอพร้อมโพสต์: {final_mp4.name}")

        ACTIVE_JOBS[job_id]["status"] = "completed"
        ACTIVE_JOBS[job_id]["progress"] = 100
        emit_log(job_id, "🏁 กระบวนการทั้งหมดเสร็จสมบูรณ์ 100% พร้อมดาวน์โหลดหรือดูพรีวิว!")

    except Exception as e:
        ACTIVE_JOBS[job_id]["status"] = "failed"
        ACTIVE_JOBS[job_id]["error"] = str(e)
        emit_log(job_id, f"❌ เกิดข้อผิดพลาด: {e}")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    """Serve the single-page dashboard HTML."""
    html_file = Path(__file__).resolve().parent / "web" / "index.html"
    if html_file.is_file():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Shopee AI Video Factory</h1><p>Web dashboard file not found.</p>")

@app.get("/api/status")
async def get_system_status():
    """System health check and environmental capabilities."""
    return {
        "status": "online",
        "ffmpeg_path": config.FFMPEG_PATH,
        "ffmpeg_ready": bool(config.FFMPEG_PATH and Path(config.FFMPEG_PATH).is_file()),
        "gemini_api_ready": bool(config.GEMINI_API_KEY),
        "min_ams_rate": config.MIN_AMS_COMMISSION_RATE,
        "chrome_debug_port": config.CHROME_DEBUG_PORT,
        "default_font": config.DEFAULT_FONT_PATH.name,
        "default_bgm": config.DEFAULT_BGM_PATH.name,
    }

@app.get("/api/products")
async def list_products():
    """Get list of tracked winning products from database."""
    db_path = config.PRODUCTS_DB_PATH
    if db_path.is_file():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

@app.get("/api/products/top10")
async def get_top10_products():
    """Return top 10 recommended winning products for Shopee Affiliate with high AMS %."""
    db_path = config.PRODUCTS_DB_PATH
    if db_path.is_file():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
                items = list(db.values())
                items.sort(key=lambda x: x.get("rank", 99))
                return items[:10]
        except Exception as e:
            print(f"Error loading top10: {e}")
            return []
    return []

@app.get("/api/product/{product_id}")
async def get_product_details(product_id: str):
    """Fetch all generated artifacts and metadata for a given product."""
    p_dir = config.OUTPUT_DIR / product_id
    if not p_dir.is_dir():
        return {"exists": False, "product_id": product_id}

    def load_json(name):
        f = p_dir / name
        if f.is_file():
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception:
                return None
        return None

    final_video = p_dir / f"final_shopee_{product_id}.mp4"
    voiceover = p_dir / "voiceover.mp3"

    return {
        "exists": True,
        "product_id": product_id,
        "product_data": load_json("product_data.json"),
        "curated_segments": load_json("curated_segments.json") or [],
        "script": load_json("script.json"),
        "audio_sub_meta": load_json("audio_sub_meta.json"),
        "video_url": f"/output/{product_id}/{final_video.name}" if final_video.is_file() else None,
        "voiceover_url": f"/output/{product_id}/{voiceover.name}" if voiceover.is_file() else None,
        "video_exists": final_video.is_file(),
        "video_size_mb": round(final_video.stat().st_size / (1024*1024), 2) if final_video.is_file() else 0,
    }

@app.post("/api/pipeline/start")
async def start_pipeline(req: PipelineRunRequest, background_tasks: BackgroundTasks):
    """Trigger the pipeline in background and return job_id for live log streaming."""
    job_id = str(uuid.uuid4())
    JOB_LOGS[job_id] = []
    ACTIVE_JOBS[job_id] = {"status": "queued", "progress": 0}
    background_tasks.add_task(run_pipeline_worker, job_id, req)
    return {"job_id": job_id, "status": "started", "product_id": req.product_id}

@app.get("/api/pipeline/logs/{job_id}")
async def stream_pipeline_logs(job_id: str):
    """Server-Sent Events (SSE) streaming live terminal output to the web UI."""
    async def log_generator():
        sent_count = 0
        while True:
            logs = JOB_LOGS.get(job_id, [])
            if sent_count < len(logs):
                for line in logs[sent_count:]:
                    yield f"data: {json.dumps({'log': line})}\n\n"
                sent_count = len(logs)

            job_state = ACTIVE_JOBS.get(job_id, {})
            if job_state.get("status") in ("completed", "failed"):
                yield f"data: {json.dumps({'status': job_state.get('status'), 'progress': job_state.get('progress')})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.post("/api/script/save")
async def update_script(req: ScriptUpdateRequest):
    """Allow user to manually tweak or refine the AI script before assembling video."""
    p_dir = config.OUTPUT_DIR / req.product_id
    p_dir.mkdir(parents=True, exist_ok=True)
    script_path = p_dir / "script.json"

    data = {
        "on_screen_headline": req.on_screen_headline,
        "hook_text": req.hook_text,
        "body_text": req.body_text,
        "cta_text": req.cta_text,
        "full_script": req.full_script,
        "updated_manually": True
    }
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "saved", "script": data}

class VoiceoverUploadRequest(BaseModel):
    product_id: str
    audio_base64: str

@app.post("/api/voiceover/upload")
async def upload_custom_voiceover(req: VoiceoverUploadRequest):
    """
    Accept user mic recording or custom MP3 upload as base64 string.
    Automatically saves it and re-aligns subtitles to the exact duration.
    """
    p_dir = config.OUTPUT_DIR / req.product_id
    p_dir.mkdir(parents=True, exist_ok=True)
    dest_audio = p_dir / "voiceover.mp3"

    raw_b64 = req.audio_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    with open(dest_audio, "wb") as f:
        f.write(base64.b64decode(raw_b64))

    # Automatically align subtitles with this custom voice
    s_file = p_dir / "script.json"
    script_data = {}
    if s_file.is_file():
        try:
            with open(s_file, "r", encoding="utf-8") as pf:
                script_data = json.load(pf)
        except Exception:
            pass

    sub_meta = generate_voiceover_and_subtitles(req.product_id, script_data, voice_choice="custom")
    return {
        "status": "success",
        "duration": sub_meta["duration"],
        "audio_url": f"/output/{req.product_id}/voiceover.mp3"
    }

if __name__ == "__main__":
    import uvicorn
    print("🌐 Starting Shopee AI Video Factory Web App on http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
