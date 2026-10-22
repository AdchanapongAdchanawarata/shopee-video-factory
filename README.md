# 🛍️ Shopee AI Affiliate Hybrid Video Factory (Thailand Market)

An automated, local-first production pipeline designed to scout high-converting Shopee Thailand products, analyze authentic Thai buyer reviews, generate persuasive "ป้ายยา" sales scripts, and assemble hybrid 9:16 vertical short videos (15–25s) with word-level Thai subtitles and anti-spam metadata scrubbing.

---

## ⚡ Core Features & Rules

1. **AMS Extra Commission Gate (CRITICAL):**
   - Automatically filters out products with standard commissions.
   - **Enforces Seller Extra Commission (AMS) >= 8.0%** to safeguard profit margins when videos are labeled with AI tags.
2. **Smart Vision Curator (OpenCV + Gemini 2.5 Flash Vision):**
   - **Stage 1 (Local CV Filter):** Rejects blurry videos (Laplacian variance < 75) and dark/overexposed clips before consuming API quota.
   - **Stage 2 (Gemini Vision Timestamps):** Uses `gemini-2.5-flash` with structured Pydantic output to extract high-scoring (1-10) segments showing clear product demonstration.
3. **Persuasive Thai Scriptwriting ("ป้ายยา" Style):**
   - Uses `gemini-2.5-flash` to extract the #1 customer pain point from 1-star reviews and the #1 praised feature from 5-star reviews.
   - Formulates a 45–60 word conversational script (~18–22s spoken duration) divided into Hook (0-3s), Body (3-15s), and CTA (15-20s).
4. **Natural Voiceover & Safe-Zone ASS Subtitles:**
   - Synthesizes speech via `edge-tts` (`th-TH-PremwadeeNeural` at +15% rate) with optional ElevenLabs toggle.
   - Generates `.ass` subtitles with bold Thai font (`Kanit-Bold`), radiant yellow/white styling, and black stroke.
   - **Safe Margin (480px / 25% height):** Subtitles are kept strictly above the Shopee orange basket UI zone.
5. **Anti-Spam Hybrid Video Assembly (FFmpeg):**
   - Cuts scenes rapidly every 1.8 - 2.2 seconds.
   - Highest-scoring `hook_action` shot placed in the first 0-3 seconds.
   - Slices and crops to 9:16 vertical (1080x1920) at 30fps.
   - Strips original camera/creator metadata (`-map_metadata -1`).
   - Applies subtle 103% zoom/scale and color grading to ensure a unique file hash.
   - Mixes voiceover with background music at 10% volume.

---

## 📁 Directory Structure

```text
shopee_killer/
├── config/
│   ├── __init__.py
│   └── settings.py             # Global settings, paths, commission thresholds, FFmpeg resolution
├── modules/
│   ├── __init__.py             # Clean unified exports
│   ├── 1_product_scout.py      # Playwright scraper (CDP / persistent session)
│   ├── 1_5_vision_curator.py   # OpenCV blur/brightness filter + Gemini Vision
│   ├── 2_script_writer.py      # Gemini 2.5 Flash Thai "ป้ายยา" script generator
│   ├── 3_voice_and_sub.py      # Thai edge-tts voiceover & safe-zone ASS subtitles
│   └── 4_video_assembler.py    # FFmpeg 9:16 hybrid video assembler & anti-spam encoder
├── assets/
│   ├── fonts/
│   │   └── Kanit-Bold.ttf      # Bold Thai display font
│   └── audio/
│       └── bgm_sample.mp3      # Upbeat royalty-free background music loop
├── data/
│   ├── products_db.json        # Tracked winning products & affiliate links
│   └── sample_product.json     # Ready-to-test mock product dataset
├── output/                     # Production output folders per product_id
├── bin/
│   └── ffmpeg.exe              # Local FFmpeg binary (auto-configured)
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
└── main.py                     # CLI Orchestrator
```

---

## 🛠️ Quickstart & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=your_gemini_api_key_here
CHROME_DEBUG_PORT=9222
MIN_AMS_COMMISSION_RATE=8.0
```

### 3. Launch Chrome with Remote Debugging (To Preserve Shopee Login)

To bypass Shopee CAPTCHA and reuse your logged-in session:

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_shopee"
```

**Windows (PowerShell):**
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeShopeeProfile"
```

---

## 🌐 ใช้งานผ่านหน้าเว็บ (Modern Web App Dashboard)

คุณสามารถเปิดใช้งานระบบผ่านหน้าเว็บกราฟิกสวยงาม (รองรับการดูวิดีโอ 9:16 บนมือถือจำลอง, อ่าน Terminal สด, และปรับแก้สคริปต์ได้ในตัว):

```bash
python server.py
```
เปิดบราวเซอร์ไปที่: **`http://localhost:8000`**

### ฟีเจอร์บนหน้าเว็บ Dashboard:
1. **Shopee Video 9:16 Simulator:** ดูพรีวิววิดีโอจริงพร้อมจำลองปุ่มถูกใจ, คอมเมนต์, และแถบตะกร้าส้ม Shopee เพื่อเช็กว่าซับไตเติลไม่ทับตะกร้า
2. **Live Console Terminal:** สตรีม Log การทำงานสดๆ จาก Python แบบ Real-time ผ่าน Server-Sent Events (SSE)
3. **Interactive Script Editor:** สามารถแก้ข้อความ Hook, Body, CTA หรือ Headline ได้เองก่อนสั่งประกอบร่างวิดีโอ
4. **Curated Segments Table:** แสดงตารางช็อตวิดีโอที่ผ่านการคัดเลือก พร้อมคะแนนความสวย (1-10) และเหตุผลที่เลือก
5. **Download Video MP4:** กดดาวน์โหลดไฟล์วิดีโอความละเอียดสูง 1080x1920 ลงเครื่องได้ทันที

---

## 🚀 Running the Pipeline (ผ่าน Command Line)

### End-to-End Test Run (Offline / Mock Mode)
Run the entire factory pipeline using the included sample cat water fountain dataset:
```bash
python main.py --product_id cat_fountain_01 --mock
```

### Live Shopee Product Run
Scrape a live Shopee product URL, extract reviews, and build the video:
```bash
python main.py --url "https://shopee.co.th/product/12345/67890" --product_id cat_fountain_01
```

### Running Individual Pipeline Steps
You can run any module individually using `--step`:

- **Step 1 (Scout & Validate AMS):**
  ```bash
  python main.py --product_id cat_fountain_01 --step 1 --mock
  ```
- **Step 1.5 (Curate Video Timestamps via OpenCV & Gemini Vision):**
  ```bash
  python main.py --product_id cat_fountain_01 --step 1.5 --mock
  ```
- **Step 2 (Generate 20s Thai Script):**
  ```bash
  python main.py --product_id cat_fountain_01 --step 2 --mock
  ```
- **Step 3 (Generate TTS & Subtitles):**
  ```bash
  python main.py --product_id cat_fountain_01 --step 3
  ```
- **Step 4 (Assemble Final 9:16 Video):**
  ```bash
  python main.py --product_id cat_fountain_01 --step 4 --duration 20.0
  ```

---

## 📊 Pipeline Output Artifacts

For each product, files are saved to `./output/{product_id}/`:
- `product_data.json`: Scraped specifications, ratings, and Thai reviews.
- `curated_segments.json`: Top action/closeup timestamps graded by visual score.
- `script.json`: Structured Hook, Body, CTA, on-screen headline, and B-roll prompts.
- `voiceover.mp3`: Synthesized Thai audio (+15% speed).
- `subtitles.ass`: Stylized ASS subtitles formatted with safe margins.
- `subtitles.srt`: Standard SRT subtitles.
- `final_shopee_{product_id}.mp4`: Ready-to-post 1080x1920 9:16 MP4 video.
