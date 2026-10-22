import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
# Ensure UTF-8 output on all systems (Windows cp1252 fix)
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ==========================================
# Paths & Directories
# ==========================================
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
AUDIO_DIR = ASSETS_DIR / "audio"
WORKSPACE_DATA_DIR = BASE_DIR / "workspace_data"
BIN_DIR = BASE_DIR / "bin"

for folder in [DATA_DIR, OUTPUT_DIR, ASSETS_DIR, FONTS_DIR, AUDIO_DIR, WORKSPACE_DATA_DIR, BIN_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

PRODUCTS_DB_PATH = DATA_DIR / "products_db.json"
SAMPLE_PRODUCT_PATH = DATA_DIR / "sample_product.json"
DEFAULT_FONT_PATH = FONTS_DIR / "Kanit-Bold.ttf"
DEFAULT_BGM_PATH = AUDIO_DIR / "bgm_sample.mp3"

# ==========================================
# FFmpeg Resolution Utility
# ==========================================
def get_ffmpeg_path() -> str:
    """Finds or configures the FFmpeg executable across Windows, macOS, and Linux."""
    # 1. Custom ENV override
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())

    # 2. Check local bin directory
    exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    local_bin = BIN_DIR / exe_name
    if local_bin.is_file():
        return str(local_bin.resolve())

    # 3. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # 4. Fallback to imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        imageio_bin = imageio_ffmpeg.get_ffmpeg_exe()
        if imageio_bin and Path(imageio_bin).is_file():
            # If on Windows, try placing a copy in BIN_DIR for standard naming
            try:
                if not local_bin.is_file():
                    shutil.copyfile(imageio_bin, local_bin)
                    return str(local_bin.resolve())
            except Exception:
                pass
            return imageio_bin
    except ImportError:
        pass

    raise RuntimeError("FFmpeg not found! Please install FFmpeg or set FFMPEG_PATH in .env")

FFMPEG_PATH = get_ffmpeg_path()
# Ensure FFmpeg directory is in PATH for any subprocesses
ffmpeg_dir = str(Path(FFMPEG_PATH).parent)
if ffmpeg_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# ==========================================
# Affiliate & Scraping Rules (Strict Constraints)
# ==========================================
MIN_AMS_COMMISSION_RATE = float(os.getenv("MIN_AMS_COMMISSION_RATE", "8.0"))  # Extra commission >= 8%
MIN_SELLER_RATING = float(os.getenv("MIN_SELLER_RATING", "4.7"))
MIN_30D_SALES = int(os.getenv("MIN_30D_SALES", "100"))
SCRAPER_DELAY_MIN = 1.5
SCRAPER_DELAY_MAX = 4.0

# Chrome / Playwright settings
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", str(WORKSPACE_DATA_DIR / "chrome_profile"))
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

# ==========================================
# AI Models & Vision Curator
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Local CV Filter Thresholds
LAPLACIAN_BLUR_THRESHOLD = 75.0
MIN_BRIGHTNESS = 40.0
MAX_BRIGHTNESS = 220.0
MIN_SHARP_RATIO = 0.40

# Script Constraints
TARGET_SCRIPT_WORDS = (45, 60)
TARGET_VIDEO_DURATION = (15.0, 25.0)

# ==========================================
# Audio & Subtitle Styling
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")  # "edge" (100% Free Studio Thai Voice), "google", or "elevenlabs"
GOOGLE_TTS_LANG = os.getenv("GOOGLE_TTS_LANG", "th")
GOOGLE_TTS_SPEED = float(os.getenv("GOOGLE_TTS_SPEED", "1.15"))


# Google Cloud Text-to-Speech (Neural2 th-TH-Neural2-C Studio-grade Thai Voice)
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "th-TH-Neural2-C")
GOOGLE_CLOUD_TTS_API_KEY = os.getenv("GOOGLE_CLOUD_TTS_API_KEY", os.getenv("GEMINI_API_KEY", ""))


EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "th-TH-PremwadeeNeural")
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "+0%")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Subtitle safe margin: keep bottom 25% clear for Shopee orange basket UI zone (1920 * 0.25 = 480px)
SUBTITLE_BOTTOM_MARGIN = 480
SUBTITLE_FONT_SIZE = 82
SUBTITLE_PRIMARY_COLOR = "&H002257FF"   # Shopee Vivid Orange (BGR: R=FF, G=57, B=22)
SUBTITLE_HIGHLIGHT_COLOR = "&H002257FF" # Shopee Vivid Orange
SUBTITLE_OUTLINE_COLOR = "&H00FFFFFF"   # Pure White Stroke / Outline
SUBTITLE_OUTLINE_WIDTH = 8.5

# ==========================================
# Video Specifications (Hybrid 9:16)
# ==========================================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_SEGMENT_DURATION = 1.8  # Fast-paced cut every 1.8 seconds
BGM_VOLUME = 0.10             # Subtle 10% background music volume
SCALE_TRANSFORM = 1.03        # 103% zoom/crop for unique hash
SPEED_TRANSFORM = 1.02        # Subtle speed shift
