import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def escape_ffmpeg_path(path: Path) -> str:
    """Escape Windows or POSIX path for FFmpeg filter_complex syntax."""
    p_str = str(path.resolve()).replace("\\", "/")
    # Escape colon on Windows drives (e.g. C:/ -> C\\:/)
    if ":" in p_str and sys.platform.startswith("win"):
        parts = p_str.split(":", 1)
        return f"{parts[0]}\\:{parts[1]}"
    return p_str

def get_video_duration(video_path: Path) -> float:
    """Get video duration using FFmpeg."""
    try:
        import re
        cmd = [config.FFMPEG_PATH, "-i", str(video_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, check=False)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if m:
            h, m_min, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + m_min * 60 + s
    except Exception:
        pass
    return 10.0

def generate_motion_clip_from_color(output_path: Path, duration: float, color: str, text: str):
    """Generate a placeholder motion clip if no raw video is available."""
    cmd = [
        config.FFMPEG_PATH, "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:d={duration}:r={config.VIDEO_FPS}",
        "-vf", f"drawtext=text='{text}':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def generate_motion_clip_from_image(
    image_path: Path,
    output_path: Path,
    duration: float = 2.5,
    motion_idx: int = 0
) -> bool:
    """
    Transforms a real high-res product photo into an ultra-clean 9:16 (1080x1920)
    Ken-Burns motion video clip with blurred aesthetic backdrop.
    """
    frames = max(30, int(duration * config.VIDEO_FPS))
    
    # 4 dynamic motion variations to keep the video energetic
    motion_patterns = [
        # 0: Smooth zoom in
        f"zoompan=z='min(zoom+0.0016,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        # 1: Smooth zoom out
        f"zoompan=z='max(1.15-0.0016*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        # 2: Subtle dynamic pan & scale
        f"zoompan=z='1.10':d={frames}:x='iw/2-(iw/zoom/2)+sin(on/25)*30':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        # 3: Slight upward float
        f"zoompan=z='1.08':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+(on/{frames})*35':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}"
    ]
    zp = motion_patterns[motion_idx % len(motion_patterns)]

    filter_complex = (
        f"split[bg_in][fg_in];"
        f"[bg_in]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"boxblur=22:5,eq=brightness=-0.12:saturation=1.25[bg];"
        f"[fg_in]scale=920:920:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        f"{zp},"
        f"setsar=1,fps={config.VIDEO_FPS}"
    )

    cmd = [
        config.FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-filter_complex", filter_complex,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return res.returncode == 0 and output_path.is_file()

def prepare_trimmed_segment(
    seg: Dict[str, Any],
    seg_idx: int,
    temp_dir: Path,
    target_dur: float
) -> Optional[Path]:
    """
    Trim, crop to 9:16 (1080x1920), apply 103% zoom/scale, and subtle color grading.
    """
    src_video = Path(seg["source_video"])
    if not src_video.is_file():
        return None

    out_seg = temp_dir / f"seg_{seg_idx:02d}.mp4"
    start_sec = max(0.0, float(seg.get("start_sec", 0.0)))
    dur = float(seg.get("duration", target_dur))
    dur = min(dur, target_dur)

    # Video filter chain:
    # 1. Scale & Crop to 9:16 (1080x1920)
    # 2. Subtle 103% scale & center crop for unique hash
    # 3. Subtle color grade (contrast 1.03, brightness 0.01, saturation 1.05)
    vf = (
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"scale={config.SCALE_TRANSFORM}*iw:{config.SCALE_TRANSFORM}*ih,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"eq=contrast=1.03:brightness=0.01:saturation=1.05,"
        f"setsar=1,fps={config.VIDEO_FPS}"
    )

    cmd = [
        config.FFMPEG_PATH, "-y",
        "-ss", str(start_sec),
        "-t", str(dur),
        "-i", str(src_video),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-an",
        "-map_metadata", "-1",
        str(out_seg)
    ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and out_seg.is_file():
        return out_seg
    else:
        print(f"⚠️ Error trimming segment {seg_idx}: {res.stderr[-200:]}")
        return None

def assemble_curated_video(
    product_id: str,
    target_duration: Optional[float] = None,
    bgm_path: Optional[Path] = None
) -> Path:
    """
    Main entry point for Module 4:
    1. Reads curated_segments.json (sorted by visual_score and hook_action).
    2. Trims and stitches segments into 1.8-2.2s cuts.
    3. Crops to 9:16 (1080x1920) with unique transform (103% zoom + color grade).
    4. Mixes Thai voiceover and BGM (at 10% volume).
    5. Burns .ass subtitles cleanly above the Shopee orange basket safe zone.
    6. Strips all original metadata (-map_metadata -1).
    """
    out_dir = config.OUTPUT_DIR / product_id
    temp_dir = out_dir / "temp_assembly"
    temp_dir.mkdir(parents=True, exist_ok=True)

    voiceover_path = out_dir / "voiceover.mp3"
    subtitles_ass = out_dir / "subtitles.ass"
    curated_json = out_dir / "curated_segments.json"
    final_output = out_dir / f"final_shopee_{product_id}.mp4"

    # Determine duration from voiceover
    voice_dur = 20.0
    if voiceover_path.is_file():
        import re
        cmd = [config.FFMPEG_PATH, "-i", str(voiceover_path)]
        r = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            voice_dur = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))

    total_target_dur = target_duration or max(15.0, min(25.0, voice_dur + 0.5))
    print(f"🎬 Assembling Hybrid Video: Target Duration {total_target_dur:.2f}s (Voiceover: {voice_dur:.2f}s)")

    # 1. Load curated segments
    segments = []
    if curated_json.is_file():
        try:
            with open(curated_json, "r", encoding="utf-8") as f:
                segments = json.load(f)
        except Exception:
            segments = []

    # Sort segments: Ensure hook_action is 1st, then descending visual_score
    segments.sort(key=lambda x: (x.get("shot_type") == "hook_action", x.get("visual_score", 0)), reverse=True)

    # 2. Process trimmed clips
    processed_clips: List[Path] = []
    accumulated_dur = 0.0
    seg_counter = 0

    if segments:
        # Loop over segments until total_target_dur is filled
        pool_idx = 0
        while accumulated_dur < total_target_dur and pool_idx < (len(segments) * 3):
            seg = segments[pool_idx % len(segments)]
            clip_target = min(config.VIDEO_SEGMENT_DURATION, total_target_dur - accumulated_dur)
            trimmed = prepare_trimmed_segment(seg, seg_counter, temp_dir, clip_target)
            if trimmed:
                processed_clips.append(trimmed)
                accumulated_dur += clip_target
                seg_counter += 1
            pool_idx += 1

    # Check for real product images in raw_media if visual clips are insufficient
    raw_media_dir = out_dir / "raw_media"
    image_exts = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    image_files = []
    if raw_media_dir.is_dir():
        for ext in image_exts:
            image_files.extend(sorted(raw_media_dir.glob(ext)))

    if accumulated_dur < total_target_dur and image_files:
        print(f"📸 Generating Ken-Burns 9:16 cuts from {len(image_files)} real product image(s)...")
        img_idx = 0
        while accumulated_dur < total_target_dur:
            cur_img = image_files[img_idx % len(image_files)]
            clip_dur = min(2.5, total_target_dur - accumulated_dur)
            if clip_dur < 0.8:
                clip_dur = total_target_dur - accumulated_dur
            clip_p = temp_dir / f"img_motion_{seg_counter:02d}.mp4"
            ok = generate_motion_clip_from_image(cur_img, clip_p, duration=clip_dur, motion_idx=seg_counter)
            if ok:
                processed_clips.append(clip_p)
                accumulated_dur += clip_dur
                seg_counter += 1
            img_idx += 1
            if img_idx > 30:  # Safety circuit breaker
                break

    # Fallback: if no video reviews AND no product images were available
    if not processed_clips:
        print("ℹ️ Creating dynamic motion b-roll sequence (no raw review videos or images found)...")
        broll_themes = [
            ("0x2c3e50", "SHOCKING PROBLEM"),
            ("0x16a085", "INNOVATIVE SOLUTION"),
            ("0x27ae60", "POWERFUL PROOF"),
            ("0xd35400", "5-STAR REVIEWS"),
            ("0xe67e22", "CLICK ORANGE BASKET")
        ]
        while accumulated_dur < total_target_dur:
            color, text = broll_themes[seg_counter % len(broll_themes)]
            clip_p = temp_dir / f"motion_{seg_counter:02d}.mp4"
            dur = min(2.0, total_target_dur - accumulated_dur)
            generate_motion_clip_from_color(clip_p, dur, color, text)
            processed_clips.append(clip_p)
            accumulated_dur += dur
            seg_counter += 1

    print(f"📦 Stitched {len(processed_clips)} fast-paced cuts (Total visual length: {accumulated_dur:.2f}s)")

    # 3. Create concat demuxer file
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in processed_clips:
            # Use forward slashes for concat file
            clean_p = str(clip.resolve()).replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    # 4. Determine BGM
    music_file = bgm_path or config.DEFAULT_BGM_PATH
    has_bgm = music_file and Path(music_file).is_file()

    # 5. Build final FFmpeg Command
    # Concat video -> Add voiceover -> Mix BGM at 10% -> Burn .ass Subtitles -> Clean Metadata
    stitched_video = temp_dir / "stitched_raw.mp4"
    concat_cmd = [
        config.FFMPEG_PATH, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(stitched_video)
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

    # Now composite Audio and Subtitles
    ffmpeg_inputs = ["-i", str(stitched_video)]
    filter_complex_parts = []

    # Voiceover input
    has_voice = voiceover_path.is_file()
    if has_voice:
        ffmpeg_inputs.extend(["-i", str(voiceover_path)])

    # BGM input
    if has_bgm:
        ffmpeg_inputs.extend(["-i", str(music_file)])

    # Subtitle burning filter: run from out_dir so subtitles.ass is relative
    # This avoids any drive letter / backslash escaping bugs on Windows!
    sub_filter = ""
    if subtitles_ass.is_file():
        # Relative path from working dir
        rel_font_dir = "../../assets/fonts"
        sub_filter = f"ass=subtitles.ass:fontsdir={rel_font_dir}"
    else:
        sub_filter = "null"

    # Audio mixing
    audio_map = ""
    if has_voice and has_bgm:
        # [1:a] is voiceover, [2:a] is BGM
        # Loop BGM, set volume to 10%, mix together
        filter_complex_parts.append(
            f"[2:a]volume={config.BGM_VOLUME},aloop=loop=-1:size=2e+09[bgm];"
            f"[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        audio_map = "[aout]"
    elif has_voice:
        audio_map = "1:a"
    elif has_bgm:
        filter_complex_parts.append(f"[1:a]volume={config.BGM_VOLUME}[aout]")
        audio_map = "[aout]"

    final_cmd = [config.FFMPEG_PATH, "-y"]
    final_cmd.extend(ffmpeg_inputs)

    # Assemble filter_complex
    if filter_complex_parts:
        final_cmd.extend(["-filter_complex", "".join(filter_complex_parts)])

    final_cmd.extend(["-vf", sub_filter])

    if audio_map:
        final_cmd.extend(["-map", "0:v", "-map", audio_map])
    else:
        final_cmd.extend(["-map", "0:v"])

    final_cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_target_dur),
        "-map_metadata", "-1",  # Anti-spam: strip original camera/creator metadata
        str(final_output)
    ])

    print("🚀 Encoding final MP4 with FFmpeg (Anti-Spam transform + burned subtitles)...")
    res = subprocess.run(final_cmd, cwd=str(out_dir), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"⚠️ FFmpeg error: {res.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg assembly failed: {res.stderr[-300:]}")

    # Cleanup temp clips
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    final_size_mb = final_output.stat().st_size / (1024 * 1024)
    print(f"🎉 Final Hybrid Video Assembled Successfully!")
    print(f"📁 Path: {final_output}")
    print(f"📊 Size: {final_size_mb:.2f} MB | Duration: {total_target_dur:.2f}s | Resolution: 1080x1920 (9:16)")

    return final_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Hybrid Video Assembler")
    parser.add_argument("--product_id", type=str, default="cat_fountain_01")
    parser.add_argument("--duration", type=float, default=20.0)
    args = parser.parse_args()

    assemble_curated_video(args.product_id, target_duration=args.duration)
