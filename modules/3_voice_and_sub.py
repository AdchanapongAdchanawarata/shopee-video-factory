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


ELEVENLABS_VOICE_MAP = {
    "elevenlabs_jessica": "cgSgspJ2msm6clMCkdW9",
    "elevenlabs_lily": "pFZP5JQG7iQjIQuC4Bku",
    "elevenlabs_laura": "FGY2WhTYpPnrIDTdsKH5",
    "elevenlabs_liam": "TX3LPaxmHKxFdv7VOQHJ",
    "elevenlabs_george": "JBFqnCBsd6RMkjVDRZzb",
    "elevenlabs_will": "bIHbv24MWmeRgasZH58o",
    "elevenlabs_brian": "nPczCjzI2devNBz1zQrb",
    "elevenlabs_mali": "7XW5JhaNn90bnFojQ5DA",
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",
    "george": "JBFqnCBsd6RMkjVDRZzb",
    "will": "bIHbv24MWmeRgasZH58o",
    "brian": "nPczCjzI2devNBz1zQrb",
    "mali": "7XW5JhaNn90bnFojQ5DA",
}

def synthesize_elevenlabs(
    text: str,
    output_path: Path,
    voice_id: str = None,
    model_id: str = "eleven_multilingual_v2"
) -> bool:
    """Synthesize studio-grade Thai speech via ElevenLabs SDK."""
    try:
        from dotenv import load_dotenv
        from elevenlabs import ElevenLabs, VoiceSettings
        
        load_dotenv(dotenv_path=config.BASE_DIR / ".env")
        client = ElevenLabs()
        
        # Resolve voice id
        target_vid = voice_id or getattr(config, "ELEVENLABS_VOICE_ID", "") or "cgSgspJ2msm6clMCkdW9"
        if target_vid in ELEVENLABS_VOICE_MAP:
            target_vid = ELEVENLABS_VOICE_MAP[target_vid]

        clean_text = format_conversational_thai_script(text)
        print(f"🎙️ Generating natural Thai voiceover via ElevenLabs SDK (voice_id: {target_vid}, model: {model_id})...")
        
        def _call_convert(v_id):
            return client.text_to_speech.convert(
                text=clean_text,
                voice_id=v_id,
                model_id=model_id,
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.8
                )
            )

        try:
            audio = _call_convert(target_vid)
        except Exception as api_err:
            # If library voice requires paid plan, fallback to verified ElevenLabs Premade voice (Jessica)
            if "paid_plan_required" in str(api_err) or "402" in str(api_err):
                fallback_vid = "cgSgspJ2msm6clMCkdW9"
                print(f"ℹ️ ElevenLabs voice requires paid plan. Automatically switching to ElevenLabs Jessica ({fallback_vid})...")
                audio = _call_convert(fallback_vid)
            else:
                raise api_err
        
        temp_raw = output_path.parent / f"temp_{output_path.stem}_elevenlabs.mp3"
        with open(temp_raw, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        if temp_raw.is_file() and temp_raw.stat().st_size > 1000:
            apply_studio_vocal_chain(temp_raw, output_audio=output_path)
            if temp_raw != output_path and temp_raw.is_file():
                temp_raw.unlink()
            print(f"✅ ElevenLabs synthesis & studio mastering successful: {output_path.name}")
            return True
    except Exception as e:
        print(f"⚠️ ElevenLabs SDK synthesis error: {e}")
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

def wrap_thai_line_safely(text: str, max_chars_per_line: int = 18) -> str:
    """
    Intelligently wrap Thai text at natural word boundaries using pythainlp newmm tokenizer.
    Ensures words (like 'แมว', 'ชาร์จเร็ว', 'ไร้สาย') are NEVER broken across lines.
    """
    if not text or "\\N" in text or "\n" in text:
        return text

    # If fits on one line cleanly, keep it intact
    if len(text) <= max_chars_per_line:
        return text

    try:
        from pythainlp import word_tokenize
        tokens = word_tokenize(text, engine="newmm")
    except Exception:
        tokens = text.split(" ") if " " in text else [text]

    if len(tokens) <= 1:
        return text

    # Balance the split point closest to half character length
    total_len = sum(len(t) for t in tokens)
    target_half = total_len / 2.0

    best_idx = 1
    best_diff = float("inf")
    current_len = 0

    for i in range(len(tokens) - 1):
        current_len += len(tokens[i])
        diff = abs(current_len - target_half)
        if diff < best_diff:
            best_diff = diff
            best_idx = i + 1

    line1 = "".join(tokens[:best_idx]).strip()
    line2 = "".join(tokens[best_idx:]).strip()

    if line1 and line2:
        return f"{line1}\\N{line2}"
    return text

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

    # 1. Write ASS Subtitles (Bigger, bolder viral font sizing + crisp outline)
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
Style: Default,Kanit,112,{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&H90000000,-1,0,0,0,100,100,0,0,1,11.0,5.0,2,70,140,{config.SUBTITLE_BOTTOM_MARGIN},1
Style: Highlight,Kanit,118,{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&H90000000,-1,0,0,0,100,100,0,0,1,11.5,5.5,2,70,140,{config.SUBTITLE_BOTTOM_MARGIN},1
Style: HookHeader,Kanit,120,{config.SUBTITLE_HIGHLIGHT_COLOR},{config.SUBTITLE_PRIMARY_COLOR},{config.SUBTITLE_OUTLINE_COLOR},&HA0000000,-1,0,0,0,100,100,0,0,1,12.0,6.0,8,50,50,370,1
Style: BadgePill,Kanit,58,&H00FFFFFF,&H000000FF,&H00181818,&HA0000000,-1,0,0,0,100,100,0,0,1,7.0,3.5,8,40,40,280,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # 1. Clean Subtitle Events: Pure Dialogue Captions (No excess badges or cluttered headers)
    for idx, seg in enumerate(segments):
        st = format_timestamp_ass(seg["start"])
        et = format_timestamp_ass(seg["end"])
        style = "Highlight" if idx % 2 == 0 else "Default"
        txt = remove_emojis_and_icons(seg["text"]).strip()
        txt = wrap_thai_line_safely(txt, max_chars_per_line=18)
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

    # 1. Synthesize voice exclusively via ElevenLabs
    success = False
    chosen_engine = (voice_choice or getattr(config, "TTS_ENGINE", "elevenlabs_jessica")).lower()

    if chosen_engine == "custom" and audio_path.is_file():
        print(f"🎙️ Using existing user recorded / uploaded audio: {audio_path.name}")
        success = True
    else:
        print(f"🎙️ Synthesizing voice via ElevenLabs AI ({chosen_engine})...")
        success = synthesize_elevenlabs(full_text, audio_path, voice_id=chosen_engine)
        if not success:
            print("⚠️ Retrying with default ElevenLabs Jessica...")
            success = synthesize_elevenlabs(full_text, audio_path, voice_id="cgSgspJ2msm6clMCkdW9")




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
