import os
import sys
import re
import json
import asyncio
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import requests

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def get_audio_duration(audio_path: Path) -> float:
    """Accurately extract duration of an audio file using FFmpeg."""
    try:
        cmd = [config.FFMPEG_PATH, "-i", str(audio_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, check=False)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))
            seconds = float(m.group(3))
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"⚠️ Error checking audio duration: {e}")
    return 20.0
def synthesize_google_cloud_neural2(
    text: str,
    output_path: Path,
    voice_name: str = None,
    speaking_rate: float = None,
    api_key: str = None
) -> bool:
    """
    Synthesize natural studio-grade Thai speech via Google Cloud Text-to-Speech Neural2 (th-TH-Neural2-C).
    Google Cloud provides 1,000,000 characters free per month (~3,000+ affiliate scripts/month).
    """
    v = voice_name or getattr(config, "GOOGLE_TTS_VOICE", "th-TH-Neural2-C")
    rate = speaking_rate if speaking_rate is not None else getattr(config, "GOOGLE_TTS_SPEED", 1.15)
    key = api_key or getattr(config, "GOOGLE_CLOUD_TTS_API_KEY", "") or getattr(config, "GEMINI_API_KEY", "")

    if not key:
        return False

    try:
        import base64
        import requests
        clean_text = format_conversational_thai_script(text)
        print(f"🎙️ Generating voice via Google Cloud TTS ({v}, Rate: {rate}x)...")
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}"
        payload = {
            "input": {"text": clean_text},
            "voice": {
                "languageCode": "th-TH",
                "name": v
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": float(rate),
                "pitch": 0.0
            }
        }
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            audio_content = data.get("audioContent")
            if audio_content:
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(audio_content))
                apply_studio_vocal_chain(output_path)
                print(f"✅ Google Cloud TTS synthesis & studio mastering successful ({v}): {output_path.name}")
                return True
        else:
            print(f"ℹ️ Google Cloud TTS response ({res.status_code}): {res.text[:120]}")
    except Exception as e:
        print(f"⚠️ Google Cloud TTS synthesis error: {e}")
    return False



def synthesize_google_tts(text: str, output_path: Path, lang: str = None, speed: float = None) -> bool:
    """Synthesize natural, authentic Thai speech via Google Text-to-Speech (gTTS)."""
    try:
        import gtts
        import shutil
        l = lang or getattr(config, "GOOGLE_TTS_LANG", "th")
        s = speed if speed is not None else getattr(config, "GOOGLE_TTS_SPEED", 1.25)
        print(f"🎙️ Generating Thai voiceover via Google TTS (lang: {l}, speed: {s}x)...")

        tts = gtts.gTTS(text=text, lang=l, slow=False)
        temp_raw = output_path.parent / f"temp_{output_path.stem}_raw.mp3"
        tts.save(str(temp_raw))

        # Adjust tempo via FFmpeg to natural affiliate short video pace
        if abs(s - 1.0) > 0.01:
            cmd = [
                config.FFMPEG_PATH, "-y",
                "-i", str(temp_raw),
                "-filter:a", f"atempo={s}",
                "-c:a", "libmp3lame",
                "-b:a", "128k",
                str(output_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            if temp_raw.is_file():
                temp_raw.unlink()
        else:
            if temp_raw != output_path:
                shutil.move(str(temp_raw), str(output_path))
        return True
    except Exception as e:
        print(f"⚠️ Google TTS synthesis failed: {e}")
        return False

def format_conversational_thai_script(text: str) -> str:
    """
    Makes Thai script flow naturally for speech synthesis:
    - Normalizes technical terms to colloquial Thai spoken words
    - Prevents robot spelling of acronyms or symbols
    """
    t = remove_emojis_and_icons(text)
    subs = [
        (r"\bUGREEN\b", "ยูกรีน"),
        (r"\bugreen\b", "ยูกรีน"),
        (r"\bGaN 65W\b", "หกสิบห้าวัตต์"),
        (r"\b65W\b", "หกสิบห้าวัตต์"),
        (r"\bGaN\b", "แกน"),
        (r"\bType-C\b", "ไทป์ซี"),
        (r"\bMacBook Pro\b", "แมคบุ๊ก"),
        (r"\bMacBook\b", "แมคบุ๊ก"),
        (r"\bDeerma\b", "เดียร์ม่า"),
        (r"\bTYESO\b", "ไทโซ่"),
        (r"\b1200ml\b", "หนึ่งพันสองร้อยมิลลิลิตร"),
        (r"\b304\b", "สามศูนย์สี่"),
        (r"\b13kPa\b", "สิบสามกิโลปาสคาล"),
        (r"\b\+\b", " และ "),
        (r"3 พอร์ต", "สามช่อง"),
    ]
    for pat, rep in subs:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    
    t = re.sub(r"([!?.,])", r"\1 ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def apply_studio_vocal_chain(input_audio: Path, output_audio: Path = None) -> Path:
    """
    Applies transparent voice enhancement via FFmpeg:
    1. Highpass at 70Hz (removes low-end rumble)
    2. Subtle presence boost (+1.5dB at 3.2kHz for vocal clarity)
    3. Transparent limiter (soft threshold, preserves natural human dynamic)
    """
    target = output_audio or input_audio
    temp_master = input_audio.parent / f"temp_master_{input_audio.stem}.mp3"
    cmd = [
        config.FFMPEG_PATH, "-y",
        "-i", str(input_audio),
        "-af", "highpass=f=70,equalizer=f=3200:t=q:w=1.0:g=1.8,alimiter=limit=0.95:attack=5:release=50",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(temp_master)
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        if temp_master.is_file() and temp_master.stat().st_size > 1000:
            import shutil
            shutil.move(str(temp_master), str(target))
            print(f"🎚️ Applied Studio Vocal Mastering Chain: {target.name}")
    except Exception as e:
        print(f"⚠️ Vocal mastering note: {e}")
        if temp_master.is_file():
            temp_master.unlink()
    return target

async def synthesize_edge_tts(text: str, output_path: Path, voice: str = None, rate: str = None, pitch: str = None) -> bool:
    """Synthesize natural Thai speech via edge-tts (100% Free, Studio Quality)."""
    try:
        import edge_tts
        v = voice or getattr(config, "EDGE_TTS_VOICE", "th-TH-PremwadeeNeural")
        r = rate or getattr(config, "EDGE_TTS_RATE", "+2%")
        p = pitch or "+1Hz"
        print(f"🎙️ Generating natural Thai voiceover via edge-tts ({v}, rate {r}, pitch {p})...")
        clean_text = format_conversational_thai_script(text)
        communicate = edge_tts.Communicate(clean_text, v, rate=r, pitch=p)
        await communicate.save(str(output_path))
        if output_path.is_file() and output_path.stat().st_size > 1000:
            # Apply vocal mastering chain to remove synthetic flat sound
            apply_studio_vocal_chain(output_path)
            print(f"✅ Edge-TTS synthesis & studio mastering successful: {output_path.name}")
            return True
    except Exception as e:
        print(f"⚠️ Edge-TTS synthesis error: {e}")
    return False


def synthesize_elevenlabs(text: str, output_path: Path) -> bool:
    """Optional ElevenLabs TTS integration if API key is provided."""
    api_key = config.ELEVENLABS_API_KEY
    voice_id = config.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"
    if not api_key:
        return False
    try:
        print("🎙️ Generating Thai voiceover via ElevenLabs API...")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
        }
        res = requests.post(url, json=data, headers=headers, timeout=30)
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(res.content)
            return True
        else:
            print(f"⚠️ ElevenLabs error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"⚠️ ElevenLabs request failed: {e}")
    return False

def format_timestamp_ass(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cc"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    centis = int(round((secs - int(secs)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{int(secs):02d}.{centis:02d}"

def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int(round((secs - int(secs)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{int(secs):02d},{millis:03d}"

def remove_emojis_and_icons(text: str) -> str:
    """Strip emojis, pictographs, and special icons for clean typography."""
    if not text:
        return ""
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]"
        "|[\u200d\u200c\u200b]"
        "|[\u2600-\u27bf]"
        "|[\ufe00-\ufe0f]"
        "|[🔥✨💧🐱🛒⭐🎉📌💡💥👉👇⭕🔴🟠]"
    )
    cleaned = emoji_pattern.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def generate_subtitles_from_phrases(
    phrases: List[str],
    total_duration: float,
    headline: str,
    output_ass: Path,
    output_srt: Path
):
    """
    Generate word/phrase-level ASS and SRT subtitles styled for Shopee / TikTok.
    Includes safe margin to keep bottom 25% clear of Shopee orange basket UI zone.
    """
    # Proportional timing based on character lengths
    clean_phrases = [remove_emojis_and_icons(p.strip()) for p in phrases if p.strip()]
    clean_phrases = [p for p in clean_phrases if p]
    if not clean_phrases:
        clean_phrases = ["คลิกตะกร้าส้มเพื่อดูรายละเอียด"]

    total_chars = sum(len(p) for p in clean_phrases)
    time_per_char = total_duration / max(1, total_chars)

    segments = []
    current_time = 0.0

    for phrase in clean_phrases:
        dur = len(phrase) * time_per_char
        end_time = current_time + dur
        segments.append({
            "start": current_time,
            "end": end_time,
            "text": phrase
        })
        current_time = end_time

    # Ensure last segment reaches total_duration
    if segments:
        segments[-1]["end"] = max(segments[-1]["end"], total_duration)

    # 1. Write ASS Subtitles
    ass_content = f"""[Script Info]
Title: Shopee Thai Dynamic Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {config.VIDEO_WIDTH}
PlayResY: {config.VIDEO_HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Kanit,82,{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&H90000000,-1,0,0,0,100,100,0,0,1,8.0,4.0,2,40,40,{config.SUBTITLE_BOTTOM_MARGIN},1
Style: Highlight,Kanit,86,{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&H90000000,-1,0,0,0,100,100,0,0,1,8.5,4.5,2,40,40,{config.SUBTITLE_BOTTOM_MARGIN},1
Style: HookHeader,Kanit,94,{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&HA0000000,-1,0,0,0,100,100,0,0,1,9.0,4.5,8,40,40,240,1
Style: BadgePill,Kanit,46,&H00FFFFFF,&H000000FF,&H00181818,&HA0000000,-1,0,0,0,100,100,0,0,1,5.5,2.5,8,30,30,130,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # 1. Add punchy hook headline for first 4.5 seconds (STRICTLY NO ICONS / EMOJIS)
    if headline:
        h_clean = remove_emojis_and_icons(headline)
        if "!" in h_clean and len(h_clean) > 16:
            parts = h_clean.split("!", 1)
            p1 = parts[0].strip() + "!"
            p2 = parts[1].strip()
            headline_formatted = f"{p1}\\N{p2}" if p2 else p1
        elif " " in h_clean and len(h_clean) > 20:
            words = h_clean.split(" ")
            mid = len(words) // 2
            p1 = " ".join(words[:mid]).strip()
            p2 = " ".join(words[mid:]).strip()
            headline_formatted = f"{p1}\\N{p2}"
        else:
            headline_formatted = h_clean

        hook_dur = min(4.5, total_duration)
        ass_content += f"Dialogue: 1,{format_timestamp_ass(0.0)},{format_timestamp_ass(hook_dur)},HookHeader,,0,0,0,,{headline_formatted}\n"

    # 2. Add Pro Proof Badges (TikTok / Shopee Influencer style)
    # Badge 1 (0.0s - 4.5s): Shopee Verified Star Rating & Sales
    b1_end = min(4.5, total_duration)
    ass_content += f"Dialogue: 2,{format_timestamp_ass(0.0)},{format_timestamp_ass(b1_end)},BadgePill,,0,0,0,,{{\\c&H00D7FF&}}★ 4.9/5{{\\c&HFFFFFF&}}  |  ยอดขายพุ่ง 3,800+ ชิ้น\n"

    # Badge 2 (4.5s - 12.0s): Authentic Guarantee Pill
    if total_duration > 5.0:
        b2_end = min(12.0, total_duration)
        ass_content += f"Dialogue: 2,{format_timestamp_ass(4.5)},{format_timestamp_ass(b2_end)},BadgePill,,0,0,0,,{{\\c&H00FF88&}}✔ ของแท้ 100%{{\\c&HFFFFFF&}}  |  สเปกตรงปก คุณภาพพรีเมียม\n"

    # Badge 3 (12.0s - End): Call to action pointer
    if total_duration > 12.0:
        ass_content += f"Dialogue: 2,{format_timestamp_ass(12.0)},{format_timestamp_ass(total_duration)},BadgePill,,0,0,0,,{{\\c&H0080FF&}}🛒 จิ้มตะกร้าส้มมุมล่างซ้ายได้เลย 👇\n"

    # 3. Add subtitle dialogue lines
    for idx, seg in enumerate(segments):
        st = format_timestamp_ass(seg["start"])
        et = format_timestamp_ass(seg["end"])
        style = "Highlight" if idx % 2 == 0 else "Default"
        txt = remove_emojis_and_icons(seg["text"])
        ass_content += f"Dialogue: 0,{st},{et},{style},,0,0,0,,{txt}\n"

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(ass_content)

    # 2. Write SRT Subtitles
    srt_lines = []
    for idx, seg in enumerate(segments, start=1):
        st = format_timestamp_srt(seg["start"])
        et = format_timestamp_srt(seg["end"])
        srt_lines.append(f"{idx}\n{st} --> {et}\n{seg['text']}\n")

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    print(f"📝 Subtitles saved:\n   - ASS: {output_ass}\n   - SRT: {output_srt}")

def split_thai_script_into_phrases(script_data: Dict[str, Any]) -> List[str]:
    """Break script into short, punchy 2-4 word phrases for high-impact viral captions."""
    parts = [
        script_data.get("hook_text", ""),
        script_data.get("body_text", ""),
        script_data.get("cta_text", "")
    ]
    connectors = [
        "หรือ", "และ", "แถม", "เพราะ", "แต่", "เซนเซอร์", "เสียงเงียบ", 
        "ล้างง่าย", "แบตอึด", "รีบกด", "ตอนนี้", "กดตะกร้า", "ฟังทางนี้",
        "สแตนเลส", "เดินผ่าน", "ไม่เป็นเมือก"
    ]
    conn_pattern = "(" + "|".join(connectors) + ")"

    phrases = []
    for part in parts:
        if not part:
            continue
        raw_chunks = re.split(r"[,!?\n]+|\s{2,}", part)
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            space_parts = [sp.strip() for sp in chunk.split(" ") if sp.strip()]
            for sp in space_parts:
                if len(sp) > 28:
                    sub_pieces = re.split(conn_pattern, sp)
                    curr = ""
                    for piece in sub_pieces:
                        if not piece:
                            continue
                        if piece in connectors and len(curr) >= 10:
                            phrases.append(curr.strip())
                            curr = piece
                        else:
                            curr += piece
                    if curr.strip():
                        phrases.append(curr.strip())
                else:
                    phrases.append(sp)

    merged = []
    for p in phrases:
        p = p.strip(" ,.!?")
        if not p:
            continue
        if len(p) <= 4 and merged:
            merged[-1] += " " + p
        else:
            merged.append(p)

    if not merged:
        full = script_data.get("full_script", "")
        merged = [full[i:i+24].strip() for i in range(0, len(full), 24) if full[i:i+24].strip()]

    return merged

def generate_voiceover_and_subtitles(
    product_id: str,
    script_data: Dict[str, Any],
    voice_choice: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for Module 3:
    1. Synthesizes Thai voiceover (or uses custom recorded/uploaded voice).
    2. Measures exact audio duration.
    3. Builds styled .ass and .srt subtitles preserving safe zone for Shopee orange basket.
    """
    out_dir = config.OUTPUT_DIR / product_id
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_path = out_dir / "voiceover.mp3"
    ass_path = out_dir / "subtitles.ass"
    srt_path = out_dir / "subtitles.srt"

    full_text = script_data.get("full_script") or f"{script_data.get('hook_text', '')} {script_data.get('body_text', '')} {script_data.get('cta_text', '')}"
    headline = script_data.get("on_screen_headline", "สินค้ายอดฮิต ป้ายยาของดี!")

    # 1. Synthesize or preserve audio
    success = False
    chosen_engine = (voice_choice or getattr(config, "TTS_ENGINE", "edge")).lower()

    CHIRP3_MAP = {
        "chirp3_aoede": "th-TH-Chirp3-HD-Aoede",
        "chirp3": "th-TH-Chirp3-HD-Aoede",
        "chirp3_callirrhoe": "th-TH-Chirp3-HD-Callirrhoe",
        "chirp3_despina": "th-TH-Chirp3-HD-Despina",
        "chirp3_achernar": "th-TH-Chirp3-HD-Achernar",
        "chirp3_achird": "th-TH-Chirp3-HD-Achird",
        "chirp3_fenrir": "th-TH-Chirp3-HD-Fenrir",
    }

    if chosen_engine == "custom" and audio_path.is_file():
        print(f"🎙️ Using existing user recorded / uploaded audio: {audio_path.name}")
        success = True
    elif chosen_engine in CHIRP3_MAP:
        v_name = CHIRP3_MAP[chosen_engine]
        print(f"🎙️ Synthesizing premium voice via Google Cloud Chirp3-HD ({v_name})...")
        success = synthesize_google_cloud_neural2(full_text, audio_path, voice_name=v_name)
    else:
        # Default to Chirp3-HD Aoede
        print("🎙️ Synthesizing voice via Google Cloud Chirp3-HD (Aoede)...")
        success = synthesize_google_cloud_neural2(full_text, audio_path, voice_name="th-TH-Chirp3-HD-Aoede")
        if not success:
            success = synthesize_google_cloud_neural2(full_text, audio_path, voice_name="th-TH-Chirp3-HD-Callirrhoe")



    duration = get_audio_duration(audio_path)
    print(f"⏱️ Voiceover generated: {audio_path.name} (Duration: {duration:.2f}s)")

    # 2. Build Subtitles
    phrases = split_thai_script_into_phrases(script_data)
    generate_subtitles_from_phrases(phrases, duration, headline, ass_path, srt_path)

    meta = {
        "audio_path": str(audio_path),
        "duration": duration,
        "ass_path": str(ass_path),
        "srt_path": str(srt_path),
        "phrases_count": len(phrases)
    }
    with open(out_dir / "audio_sub_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Thai Voice & Subtitle Generator")
    parser.add_argument("--product_id", type=str, default="cat_fountain_01")
    args = parser.parse_args()

    script_file = config.OUTPUT_DIR / args.product_id / "script.json"
    if script_file.is_file():
        with open(script_file, "r", encoding="utf-8") as f:
            s_data = json.load(f)
    else:
        s_data = {
            "full_script": "ใครที่น้องแมวดื่มน้ำน้อย หรือกลัวเรื่องสายไฟช็อต ฟังทางนี้ด่วน! ตัวนี้เป็นน้ำพุแมวไร้สาย สแตนเลส 304 แท้ เซนเซอร์อัจฉริยะ แบตอึดเป็นเดือน ล้างง่าย รีบกดที่ตะกร้าสีส้มด่วนเลย!",
            "on_screen_headline": "ทาสแมวต้องดู! น้ำพุไร้สายตัวจบ"
        }

    generate_voiceover_and_subtitles(args.product_id, s_data)
