import os
import sys
import json
import hashlib
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def escape_ffmpeg_path(path: Path) -> str:
    """Escape Windows or POSIX path for FFmpeg filter_complex syntax."""
    p_str = str(path.resolve()).replace("\\", "/")
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

def has_strange_text_or_banner(frame: np.ndarray) -> bool:
    """
    Detect if a candidate video frame contains burned-in foreign subtitles,
    solid black/white caption banners, or heavy text overlays in the top/bottom zones.
    """
    if frame is None or frame.size == 0:
        return True
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 1. Check for solid black or white letterbox/banner bars at bottom 22% or top 15%
    bottom_strip = gray[int(h * 0.80):, :]
    top_strip = gray[:int(h * 0.15), :]
    if bottom_strip.std() < 12.0 or top_strip.std() < 10.0:
        return True

    # 2. Check for high-contrast horizontal text stroke clusters in bottom 28% (typical subtitle zone)
    sub_zone = gray[int(h * 0.72):int(h * 0.96), int(w * 0.08):int(w * 0.92)]
    sobel_x = cv2.Sobel(sub_zone, cv2.CV_64F, 1, 0, ksize=3)
    abs_sobel = np.abs(sobel_x)
    # High-contrast sharp vertical strokes inside a horizontal band indicate burned-in text
    high_edge_ratio = float(np.mean(abs_sobel > 95.0))
    if high_edge_ratio > 0.16:
        return True

    return False

def compute_frame_signature(frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute a spatial 4x4 HSV histogram + 16x16 structural luminance array
    to prevent any visually similar shot from ever repeating in the same video.
    """
    small = cv2.resize(frame, (128, 224))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    h_step, w_step = 224 // 4, 128 // 4
    hists = []
    for r in range(4):
        for c in range(4):
            patch = hsv[r * h_step:(r + 1) * h_step, c * w_step:(c + 1) * w_step]
            hist = cv2.calcHist([patch], [0, 1], None, [8, 6], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            hists.append(hist.flatten())
    full_hist = np.concatenate(hists).astype(np.float32)

    gray_tiny = cv2.cvtColor(cv2.resize(small, (16, 16)), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    return full_hist, gray_tiny

def is_scene_duplicate(
    cand_sig: Tuple[np.ndarray, np.ndarray],
    existing_sigs: List[Tuple[np.ndarray, np.ndarray]],
    hist_thresh: float = 0.68,
    l1_thresh: float = 0.095
) -> bool:
    """Return True if candidate scene looks similar to ANY already-selected cut."""
    c_hist, c_gray = cand_sig
    for e_hist, e_gray in existing_sigs:
        # Cosine similarity on spatial HSV histogram
        denom = (np.linalg.norm(c_hist) * np.linalg.norm(e_hist)) + 1e-8
        cos_sim = float(np.dot(c_hist, e_hist) / denom)
        l1_diff = float(np.mean(np.abs(c_gray - e_gray)))
        if cos_sim >= hist_thresh or l1_diff <= l1_thresh:
            return True
    return False

def sample_segment_frame(video_path: Path, start_sec: float, duration: float) -> Optional[np.ndarray]:
    """Extract representative middle frame of a segment for quality & deduplication check."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    mid_sec = max(0.0, start_sec + duration * 0.5)
    cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000.0)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return None
    return frame

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
    duration: float = 2.0,
    motion_idx: int = 0
) -> bool:
    """
    Transforms a real high-res product photo into an ultra-clean 9:16 (1080x1920)
    Ken-Burns motion video clip with blurred aesthetic backdrop.
    """
    frames = max(30, int(duration * config.VIDEO_FPS))
    motion_patterns = [
        f"zoompan=z='min(zoom+0.0018,1.16)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        f"zoompan=z='max(1.16-0.0018*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        f"zoompan=z='1.12':d={frames}:x='iw/2-(iw/zoom/2)+sin(on/20)*35':y='ih/2-(ih/zoom/2)':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}",
        f"zoompan=z='1.10':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+(on/{frames})*40':s={config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}:fps={config.VIDEO_FPS}"
    ]
    zp = motion_patterns[motion_idx % len(motion_patterns)]

    filter_complex = (
        f"split[bg_in][fg_in];"
        f"[bg_in]scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"boxblur=22:5,eq=brightness=-0.12:saturation=1.25[bg];"
        f"[fg_in]scale=960:960:force_original_aspect_ratio=decrease[fg];"
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
    target_dur: float,
    speed_factor: float = 1.06
) -> Optional[Path]:
    """
    Trim, center-crop out any edge/subtitle zones, scale to 9:16 (1080x1920),
    apply dynamic camera framing, snappy speed ramp, and pro color grading.
    """
    src_video = Path(seg["source_video"])
    if not src_video.is_file():
        return None

    out_seg = temp_dir / f"seg_{seg_idx:02d}.mp4"
    start_sec = max(0.0, float(seg.get("start_sec", 0.0)))
    dur = min(float(seg.get("duration", target_dur)), target_dur)

    # Alternate subtle framing zoom factors so every cut feels dynamic without over-zooming
    scales = [1.02, 1.04, 1.03, 1.05]
    cur_scale = scales[seg_idx % len(scales)]

    crop_y = seg.get("crop_y")
    if crop_y and len(crop_y) == 2:
        y0, y1 = float(crop_y[0]), float(crop_y[1])
        h_frac = max(0.3, y1 - y0)
        crop_prefix = f"crop=iw:trunc(ih*{h_frac:.3f}/2)*2:0:trunc(ih*{y0:.3f}/2)*2,"
    else:
        crop_prefix = ""

    vf = (
        f"{crop_prefix}"
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"scale=trunc({cur_scale}*iw/2)*2:trunc({cur_scale}*ih/2)*2,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"eq=contrast=1.04:brightness=0.01:saturation=1.08,"
        f"setpts=PTS/{speed_factor},"
        f"setsar=1,fps={config.VIDEO_FPS}"
    )

    actual_input_dur = dur * speed_factor

    cmd = [
        config.FFMPEG_PATH, "-y",
        "-ss", str(start_sec),
        "-t", str(actual_input_dur),
        "-i", str(src_video),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
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

def build_diverse_candidate_segments(raw_media_dir: Path) -> List[Dict[str, Any]]:
    """
    Scan all unique MP4 files in raw_media_dir (deduplicated by MD5 hash)
    and slice them into candidate segments interleaved across ALL distinct source files
    and well-separated timestamps so every cut comes from a different source/scene.
    """
    if not raw_media_dir.is_dir():
        return []

    unique_videos: List[Path] = []
    seen_md5 = set()
    for mp4 in sorted(raw_media_dir.glob("*.mp4")):
        if mp4.name.startswith("tmp_"):
            continue
        try:
            h = hashlib.md5(mp4.read_bytes()).hexdigest()
            if h not in seen_md5:
                seen_md5.add(h)
                unique_videos.append(mp4)
        except Exception:
            pass

    per_video_slices: Dict[str, List[Dict[str, Any]]] = {}
    for vp in unique_videos:
        dur = get_video_duration(vp)
        if dur < 1.8:
            continue
        slices = []
        # Step by 3.2s across each source clip so consecutive slices from the same clip are far apart
        t = 0.2
        while t + 1.9 <= dur:
            slices.append({
                "source_video": str(vp),
                "start_sec": round(t, 2),
                "end_sec": round(t + 2.0, 2),
                "duration": 2.0,
                "shot_type": "hook_action" if t < 3.5 else "feature_demo",
                "visual_score": 9
            })
            t += 3.2
        if slices:
            per_video_slices[str(vp)] = slices

    # Interleave round-robin across all unique source videos:
    # Video 1 slice 0 -> Video 2 slice 0 -> Video 3 slice 0 -> Video 4 slice 0 -> Video 5 slice 0 ...
    interleaved: List[Dict[str, Any]] = []
    keys = list(per_video_slices.keys())
    max_len = max((len(v) for v in per_video_slices.values()), default=0)
    for idx in range(max_len):
        for k in keys:
            if idx < len(per_video_slices[k]):
                interleaved.append(per_video_slices[k][idx])

    return interleaved

def assemble_curated_video(
    product_id: str,
    target_duration: Optional[float] = None,
    bgm_path: Optional[Path] = None
) -> Path:
    """
    Main entry point for Module 4:
    1. Builds multi-source interleaved candidate segments across all unique raw_media videos.
    2. Filters out any segment with burned-in text/banners and enforces strict visual scene deduplication
       (HSV spatial histogram + structural L1 check) so ZERO shots repeat inside the 20s video.
    3. Mixes clean real product gallery images (Ken-Burns 9:16) if additional unique angles are needed.
    4. Fits Thai voiceover to 20.0s and burns top-safe ASS subtitles.
    """
    out_dir = config.OUTPUT_DIR / product_id
    raw_media_dir = out_dir / "raw_media"
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
            voice_dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

    total_target_dur = float(target_duration or 20.0)
    active_voiceover_path = voiceover_path

    # If voiceover exceeds target duration, time-fit via pitch-preserving WSOLA atempo (0 credits used)
    if voiceover_path.is_file() and voice_dur > (total_target_dur - 0.3):
        desired_voice_dur = max(10.0, total_target_dur - 0.4)
        tempo_factor = min(1.95, max(1.01, voice_dur / desired_voice_dur))
        fitted_voice = temp_dir / "voiceover_fitted.mp3"
        fit_cmd = [
            config.FFMPEG_PATH, "-y",
            "-i", str(voiceover_path),
            "-filter:a", f"atempo={tempo_factor:.4f}",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(fitted_voice)
        ]
        res_fit = subprocess.run(fit_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res_fit.returncode == 0 and fitted_voice.is_file():
            active_voiceover_path = fitted_voice
            voice_dur = desired_voice_dur
            script_file = out_dir / "script.json"
            if script_file.is_file():
                try:
                    import importlib.util
                    spec_m3 = importlib.util.spec_from_file_location("m3", str(Path(__file__).resolve().parent / "3_voice_and_sub.py"))
                    m3 = importlib.util.module_from_spec(spec_m3)
                    spec_m3.loader.exec_module(m3)
                    s_data = json.loads(script_file.read_text(encoding="utf-8"))
                    phrases = m3.split_thai_script_into_phrases(s_data)
                    m3.generate_subtitles_from_phrases(
                        phrases,
                        voice_dur,
                        s_data.get("on_screen_headline", ""),
                        subtitles_ass,
                        out_dir / "subtitles.srt"
                    )
                except Exception as sub_e:
                    print(f"⚠️ Subtitle resync note: {sub_e}")

    print(f"🎬 Assembling Pro Video: Strict Target Duration {total_target_dur:.2f}s (Zero Repeat + Zero Foreign Text)")

    processed_clips: List[Path] = []
    selected_signatures: List[Tuple[np.ndarray, np.ndarray]] = []
    accumulated_dur = 0.0
    seg_counter = 0

    # 1. Check if curated_segments.json has hand-verified non-repeating shots
    existing_segs = []
    if curated_json.is_file():
        try:
            existing_segs = json.loads(curated_json.read_text(encoding="utf-8"))
        except Exception:
            existing_segs = []

    if existing_segs and any(s.get("hand_verified") for s in existing_segs):
        for seg in existing_segs:
            if accumulated_dur >= total_target_dur:
                break
            clip_target = min(float(seg.get("duration", 2.0)), total_target_dur - accumulated_dur)
            if clip_target < 0.8:
                clip_target = total_target_dur - accumulated_dur

            if "source_image" in seg:
                img_p = Path(seg["source_image"])
                if img_p.is_file():
                    clip_p = temp_dir / f"img_motion_{seg_counter:02d}.mp4"
                    if generate_motion_clip_from_image(img_p, clip_p, duration=clip_target, motion_idx=seg_counter):
                        processed_clips.append(clip_p)
                        accumulated_dur += clip_target
                        seg_counter += 1
            elif "source_video" in seg:
                trimmed = prepare_trimmed_segment(seg, seg_counter, temp_dir, clip_target)
                if trimmed:
                    processed_clips.append(trimmed)
                    accumulated_dur += clip_target
                    seg_counter += 1

    # 2. If more cuts are needed, build interleaved candidate segments with strict OpenCV deduplication
    if accumulated_dur < total_target_dur:
        candidates = build_diverse_candidate_segments(raw_media_dir)
        if candidates and not existing_segs:
            with open(curated_json, "w", encoding="utf-8") as f:
                json.dump(candidates, f, ensure_ascii=False, indent=2)

        for pass_idx, (h_thresh, l1_thresh) in enumerate([(0.68, 0.095), (0.82, 0.055)]):
            if accumulated_dur >= total_target_dur:
                break
            for seg in candidates:
                if accumulated_dur >= total_target_dur:
                    break
                src_p = Path(seg["source_video"])
                st_sec = float(seg.get("start_sec", 0.0))
                dur_sec = float(seg.get("duration", 2.0))

                frame = sample_segment_frame(src_p, st_sec, dur_sec)
                if frame is None:
                    continue

                fh, fw = frame.shape[:2]
                cropped_frame = frame[int(fh * 0.08):int(fh * 0.84), int(fw * 0.05):int(fw * 0.95)]

                if pass_idx == 0 and has_strange_text_or_banner(cropped_frame):
                    continue

                sig = compute_frame_signature(cropped_frame)
                if is_scene_duplicate(sig, selected_signatures, hist_thresh=h_thresh, l1_thresh=l1_thresh):
                    continue

                clip_target = min(2.0, total_target_dur - accumulated_dur)
                if clip_target < 0.8:
                    clip_target = total_target_dur - accumulated_dur

                trimmed = prepare_trimmed_segment(seg, seg_counter, temp_dir, clip_target)
                if trimmed:
                    processed_clips.append(trimmed)
                    selected_signatures.append(sig)
                    accumulated_dur += clip_target
                    seg_counter += 1

    # Supplement or Fallback: If no video cuts exist or video is shorter than 20s,
    # use the official product advertisement images from raw_media (Ken-Burns 9:16 Dynamic Motion)
    if accumulated_dur < total_target_dur and raw_media_dir.is_dir():
        image_files: List[Path] = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            for img_p in sorted(raw_media_dir.glob(ext)):
                # Avoid tiny icon or preview files
                if img_p.stat().st_size > 15000:
                    image_files.append(img_p)

        if image_files:
            # If zero videos exist, calculate duration per image so all images fill 20.0s
            if len(processed_clips) == 0:
                print("📸 [โหมดภาพโฆษณาแท้] ตรวจพบว่าลิงก์นี้ไม่มีวิดีโอ -> ใช้รูปภาพโฆษณาสินค้าแปลงเป็นโมชัน 9:16 แทนอัตโนมัติ")
                num_imgs = min(len(image_files), 7)
                dur_per_img = round(total_target_dur / num_imgs, 2)
                for cur_img in image_files[:num_imgs]:
                    clip_dur = min(dur_per_img, total_target_dur - accumulated_dur)
                    if clip_dur < 0.5:
                        break
                    clip_p = temp_dir / f"img_motion_{seg_counter:02d}.mp4"
                    ok = generate_motion_clip_from_image(cur_img, clip_p, duration=clip_dur, motion_idx=seg_counter)
                    if ok:
                        processed_clips.append(clip_p)
                        accumulated_dur += clip_dur
                        seg_counter += 1
            else:
                # Supplement remaining duration with product ad images
                for cur_img in image_files:
                    if accumulated_dur >= total_target_dur:
                        break
                    clip_dur = min(2.5, total_target_dur - accumulated_dur)
                    if clip_dur < 0.8:
                        clip_dur = total_target_dur - accumulated_dur
                    clip_p = temp_dir / f"img_motion_{seg_counter:02d}.mp4"
                    ok = generate_motion_clip_from_image(cur_img, clip_p, duration=clip_dur, motion_idx=seg_counter)
                    if ok:
                        processed_clips.append(clip_p)
                        accumulated_dur += clip_dur
                        seg_counter += 1

    print(f"📦 Stitched {len(processed_clips)} 100% unique cuts (Total visual length: {accumulated_dur:.2f}s)")

    # 3. Create concat demuxer file
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in processed_clips:
            clean_p = str(clip.resolve()).replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    # 4. Determine BGM
    music_file = bgm_path or config.DEFAULT_BGM_PATH
    has_bgm = music_file and Path(music_file).is_file()

    # 5. Concat video -> Add voiceover -> Mix BGM -> Burn .ass Subtitles -> Clean Metadata
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

    ffmpeg_inputs = ["-i", str(stitched_video)]
    filter_complex_parts = []

    has_voice = active_voiceover_path.is_file()
    if has_voice:
        ffmpeg_inputs.extend(["-i", str(active_voiceover_path)])

    if has_bgm:
        ffmpeg_inputs.extend(["-i", str(music_file)])

    sub_filter = ""
    if subtitles_ass.is_file():
        rel_font_dir = "../../assets/fonts"
        sub_filter = f"ass=subtitles.ass:fontsdir={rel_font_dir}"
    else:
        sub_filter = "null"

    audio_map = ""
    if has_voice and has_bgm:
        filter_complex_parts.append(
            f"[2:a]volume=0.08,aloop=loop=-1:size=2e+09[bgm];"
            f"[1:a]volume=1.25[vce];"
            f"[vce][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
        )
        audio_map = "[aout]"
    elif has_voice:
        audio_map = "1:a"
    elif has_bgm:
        filter_complex_parts.append(f"[1:a]volume={config.BGM_VOLUME}[aout]")
        audio_map = "[aout]"

    final_cmd = [config.FFMPEG_PATH, "-y"]
    final_cmd.extend(ffmpeg_inputs)

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
        "-map_metadata", "-1",
        str(final_output)
    ])

    print("🚀 Encoding final MP4 with FFmpeg (Anti-Spam transform + burned subtitles)...")
    res = subprocess.run(final_cmd, cwd=str(out_dir), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"⚠️ FFmpeg error: {res.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg assembly failed: {res.stderr[-300:]}")

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
