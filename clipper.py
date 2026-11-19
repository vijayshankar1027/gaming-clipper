import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("❌ Error: yt-dlp is not installed. Run: pip install yt-dlp")
    sys.exit(1)

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Font selection with cross-platform fallback (Windows / Linux / Cloud)
FONT_IMPACT = "C:/Windows/Fonts/impact.ttf"
if os.path.exists(FONT_IMPACT):
    CHOSEN_FONT = "Impact"
else:
    CHOSEN_FONT = "Arial"

# YuNet AI Model Path & Auto-Download
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet.onnx"
YUNET_URL = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def ensure_yunet_model():
    """Auto-downloads YuNet model if not present or corrupt."""
    if not YUNET_MODEL_PATH.exists() or YUNET_MODEL_PATH.stat().st_size < 10000:
        print("⬇️ Downloading YuNet AI Face Detection Model...")
        import urllib.request
        try:
            urllib.request.urlretrieve(YUNET_URL, str(YUNET_MODEL_PATH))
            print("✅ YuNet Model Downloaded Successfully!")
        except Exception as e:
            print(f"⚠️ Could not download YuNet model: {e}")



# Presets for manual selection:
CALIBRATED_PRESETS = {
    "0": {
        "name": "🤖 AI Auto-Detect (Gamer ka REAL Face aur Reaction scan karega)",
        "crop": None
    },
    "1": {
        "name": "Top-Right Cam (Dattrax / GTA Streamers / BeastBoyShub)",
        "crop": "crop=370:280:1530:6",
        "w": 370,
        "h": 280
    },
    "2": {
        "name": "Mid-Left Cam (CarryMinati / Scout)",
        "crop": "crop=376:258:13:478",
        "w": 376,
        "h": 258
    },
    "3": {
        "name": "Bottom-Right Cam (Techno Gamerz / Total Gaming / Dynamo)",
        "crop": "crop=380:285:1520:780",
        "w": 380,
        "h": 285
    },
    "4": {
        "name": "Bottom-Left Cam (Mythpat / Mortal)",
        "crop": "crop=380:285:20:780",
        "w": 380,
        "h": 285
    },
    "5": {
        "name": "🚫 No Facecam (Video mein camera nahi hai — Fullscreen Gameplay Only)",
        "crop": "NO_CAM",
        "w": 0,
        "h": 0
    }
}


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def time_to_sec(t_str: str) -> float:
    """Convert HH:MM:SS.mmm to seconds."""
    parts = t_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(parts[0])


def sec_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS format: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def sanitize_filename(name: str) -> str:
    """Clean filename of invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


COOKIES_FILE = BASE_DIR / "cookies.txt"

def get_cookie_opts():
    """Returns cookiefile option if cookies.txt is present."""
    if COOKIES_FILE.exists():
        return {"cookiefile": str(COOKIES_FILE)}
    return {}


def get_video_info(url: str):
    """Extract metadata including heatmap and live status from YouTube."""
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        **get_cookie_opts()
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


# ---------------------------------------------------------------------------
# INTELLIGENT AI WEBCAM DETECTOR (OpenCV YuNet Neural Face Scanner)
# Groups detections by streamer corner to isolate stationary webcam PIP
# ---------------------------------------------------------------------------
def detect_gamer_facecam_ai(video_path: str):
    """
    Scans video frames across streamer corners using neural face detection.
    Groups detections by corner to avoid false positives from gameplay backgrounds.
    Returns (crop_filter, scale_w, scale_h).
    """
    default_crop = "crop=370:280:1530:6", 380, 287

    ensure_yunet_model()

    if not HAS_CV2 or not YUNET_MODEL_PATH.exists():
        return default_crop

    try:
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ret, f = cap.read()
            if not ret or len(frames) >= 60:
                break
            frames.append(f)
        cap.release()

        if not frames:
            return default_crop

        h, w, _ = frames[0].shape
        detector = cv2.FaceDetectorYN_create(str(YUNET_MODEL_PATH), "", (w, h), score_threshold=0.60)
        detector.setInputSize((w, h))

        sample_indices = np.linspace(0, len(frames) - 1, min(24, len(frames))).astype(int)

        corners = {
            "top_right": {"faces": [], "name": "Top-Right"},
            "mid_left": {"faces": [], "name": "Mid-Left"},
            "bottom_right": {"faces": [], "name": "Bottom-Right"},
            "bottom_left": {"faces": [], "name": "Bottom-Left"},
            "top_left": {"faces": [], "name": "Top-Left"}
        }

        for idx in sample_indices:
            _, faces = detector.detect(frames[idx])
            if faces is not None:
                for face in faces:
                    fx, fy, fw, fh = map(int, face[0:4])
                    cx, cy = fx + fw // 2, fy + fh // 2

                    if cx > w * 0.65 and cy < h * 0.45:
                        corners["top_right"]["faces"].append((cx, cy, fw, fh))
                    elif cx < w * 0.35 and h * 0.35 < cy < h * 0.85:
                        corners["mid_left"]["faces"].append((cx, cy, fw, fh))
                    elif cx > w * 0.65 and cy > h * 0.55:
                        corners["bottom_right"]["faces"].append((cx, cy, fw, fh))
                    elif cx < w * 0.35 and cy > h * 0.55:
                        corners["bottom_left"]["faces"].append((cx, cy, fw, fh))
                    elif cx < w * 0.35 and cy < h * 0.35:
                        corners["top_left"]["faces"].append((cx, cy, fw, fh))

        # Find corner with highest consistent detections
        best_corner = None
        max_count = 0
        for cname, cdata in corners.items():
            cnt = len(cdata["faces"])
            if cnt > max_count:
                max_count = cnt
                best_corner = cname

        if best_corner and max_count >= 4:
            cfaces = corners[best_corner]["faces"]
            xs = [f[0] for f in cfaces]
            ys = [f[1] for f in cfaces]

            # Consistent stationary camera
            if float(np.std(xs)) < 50 and float(np.std(ys)) < 50:
                med_x = int(np.median(xs))
                med_y = int(np.median(ys))
                med_fw = int(np.median([f[2] for f in cfaces]))
                med_fh = int(np.median([f[3] for f in cfaces]))

                cam_w = min(400, max(350, int(med_fw * 3.8)))
                cam_h = min(300, max(260, int(med_fh * 3.2)))
                crop_x = max(0, min(w - cam_w, med_x - cam_w // 2))
                crop_y = max(0, min(h - cam_h, med_y - int(med_fh * 0.85)))

                scale_w = 380
                scale_h = int(380 * cam_h / cam_w)

                print(f"   🤖 REAL GAMER FACECAM DETECTED in {corners[best_corner]['name']} at ({crop_x}, {crop_y})!")
                print(f"   📐 Tight Camera Crop: x={crop_x}, y={crop_y}, w={cam_w}, h={cam_h} → Scale: {scale_w}×{scale_h}")
                return f"crop={cam_w}:{cam_h}:{crop_x}:{crop_y}", scale_w, scale_h

        # Fallback to calibrated Top-Right
        print("   📐 Using calibrated Top-Right preset as reliable default")
        return "crop=370:280:1530:6", 380, 287

    except Exception as e:
        print(f"   ⚠️ Face detection note: {e}")
        return "crop=370:280:1530:6", 380, 287


def get_cam_filter_and_scale(preset_choice: str, video_path: str):
    """Returns (crop_filter, scale_w, scale_h) based on preset or AI detection."""
    if preset_choice == "5":
        return None, 0, 0

    if preset_choice == "0" or preset_choice not in CALIBRATED_PRESETS:
        crop_f, sw, sh = detect_gamer_facecam_ai(video_path)
        return crop_f, sw, sh

    p = CALIBRATED_PRESETS[preset_choice]
    if p["crop"] == "NO_CAM":
        return None, 0, 0

    cw, ch = p["w"], p["h"]
    scale_w = 380
    scale_h = int(380 * ch / cw)
    print(f"   📐 Using Selected Preset: {p['name']}")
    return p["crop"], scale_w, scale_h


def find_crazy_moments(info: dict, num_clips: int = 5, clip_duration: int = 45):
    """
    Detect multiple 'CRAZY' viral moments:
    - Points where viewers replayed the most (heat peaks)
    - Ensures clips are spaced out across the stream for variety
    """
    heatmap = info.get("heatmap")
    duration = info.get("duration", 0)

    selected_clips = []
    min_gap_seconds = max(90, clip_duration * 2)

    if heatmap:
        valid_points = [
            p for p in heatmap
            if p.get("start_time", 0) >= 30.0 and p.get("value") is not None
        ]
        sorted_points = sorted(valid_points, key=lambda x: x["value"], reverse=True)

        for point in sorted_points:
            peak_time = (point["start_time"] + point["end_time"]) / 2.0
            too_close = any(abs(peak_time - c["peak_time"]) < min_gap_seconds for c in selected_clips)
            if too_close:
                continue

            start_sec = max(0.0, peak_time - 15.0)
            end_sec = start_sec + clip_duration
            if duration and end_sec > duration:
                end_sec = duration
                start_sec = max(0.0, end_sec - clip_duration)

            intensity = int(point["value"] * 100)
            selected_clips.append({
                "peak_time": peak_time,
                "start_time": start_sec,
                "end_time": end_sec,
                "score": point["value"],
                "reason": f"High Replay Peak ({intensity}% intensity)"
            })

            if len(selected_clips) >= num_clips:
                break

    if len(selected_clips) < num_clips and duration:
        needed = num_clips - len(selected_clips)
        step = duration / (needed + 1)
        for i in range(1, needed + 1):
            s = int(step * i)
            e = s + clip_duration
            selected_clips.append({
                "peak_time": s + 15,
                "start_time": s,
                "end_time": e,
                "score": 0.6,
                "reason": f"Action Stream Segment #{i}"
            })

    selected_clips.sort(key=lambda x: x["start_time"])
    return selected_clips


def download_clip_section(url: str, start_sec: float, end_sec: float, output_path: str):
    """Download only the exact segment in HD MP4 using yt-dlp."""
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best",
        "download_ranges": yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
        "outtmpl": output_path,
        "force_keyframes_at_cuts": True,
        "quiet": True,
        "no_warnings": True,
        "overwrites": True,
        **get_cookie_opts()
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def fetch_spoken_subtitles(url: str, clip_start: float, clip_end: float) -> list:
    """Download YouTube auto-captions and extract spoken dialogue for this segment."""
    vtt_temp = TEMP_DIR / "stream_subs"
    ydl_opts = {
        "skip_download": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["hi", "en", "en-US", "hi-Latn"],
        "outtmpl": str(vtt_temp),
        "quiet": True,
        "no_warnings": True,
        **get_cookie_opts()
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        pass

    vtt_files = list(TEMP_DIR.glob("stream_subs*.vtt"))
    if not vtt_files:
        return []

    spoken_lines = []
    try:
        content = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
        cues = re.findall(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})[^\n]*\n([\s\S]*?)(?=\n\n|\Z)",
            content
        )
        last_clean = ""
        for start_str, end_str, raw_text in cues:
            s = time_to_sec(start_str)
            e = time_to_sec(end_str)
            if e > clip_start and s < clip_end:
                rel_s = max(0.0, s - clip_start)
                rel_e = min(clip_end - clip_start, e - clip_start)
                clean = re.sub(r"<[^>]+>", "", raw_text)
                clean = re.sub(r"\[.*?\]", "", clean).strip()
                if clean and clean != last_clean:
                    last_clean = clean
                    spoken_lines.append((rel_s, rel_e, clean.upper()))
    except Exception:
        pass
    finally:
        for f in vtt_files:
            try:
                f.unlink()
            except Exception:
                pass

    return spoken_lines


def generate_cinematic_ass(spoken_dialogues: list, ass_path: Path):
    """
    Creates cinematic ASS subtitles:
    - Bold Yellow font with 5px black outline + soft shadow (TikTok style)
    - Positioned at lower-third (MarginV=260)
    """
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: SpokenText,{CHOSEN_FONT},52,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,40,40,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if spoken_dialogues:
        for rel_s, rel_e, text in spoken_dialogues:
            ass_content += f"Dialogue: 0,{sec_to_ass_time(rel_s)},{sec_to_ass_time(rel_e)},SpokenText,,0,0,0,,{text}\n"
    else:
        ass_content += "Dialogue: 0,0:00:01.00,0:00:04.50,SpokenText,,0,0,0,,CRAZY MOMENT! 🔥\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


def render_pip_clip(
    input_video: str,
    output_video: str,
    ass_path: Path,
    crop_filter: str = None,
    cam_scale_w: int = 0,
    cam_scale_h: int = 0,
    cam_position: str = "right-corner"
):
    """
    Renders 9:16 Video:
    - Main Gameplay fullscreen 9:16 background
    - Tight Fit Gamer Camera Overlay on Right Corner (or chosen position)
    - Cinematic subtitles in lower third
    """
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    bg_w, bg_h = 1080, 1920
    margin_x = 25
    margin_y = 40

    if cam_position == "right-corner":
        x_expr = f"{bg_w} - w - {margin_x}"
        y_expr = f"{margin_y}"
    elif cam_position == "left-corner":
        x_expr = f"{margin_x}"
        y_expr = f"{margin_y}"
    elif cam_position == "top-center":
        x_expr = "(W - w) / 2"
        y_expr = f"{margin_y}"
    elif cam_position == "bottom-right":
        x_expr = f"{bg_w} - w - {margin_x}"
        y_expr = f"{bg_h} - h - 380"
    elif cam_position == "bottom-left":
        x_expr = f"{margin_x}"
        y_expr = f"{bg_h} - h - 380"
    else:
        x_expr = f"{bg_w} - w - {margin_x}"
        y_expr = f"{margin_y}"

    if crop_filter:
        filter_complex = (
            f"[0:v]crop=ih*(9/16):ih:(iw-ih*(9/16))/2:0,scale=1080:1920[gameplay];"
            f"[0:v]{crop_filter},scale={cam_scale_w}:{cam_scale_h}[cam];"
            f"[gameplay][cam]overlay={x_expr}:{y_expr},ass='{ass_escaped}'"
        )
    else:
        filter_complex = (
            f"[0:v]crop=ih*(9/16):ih:(iw-ih*(9/16))/2:0,scale=1080:1920,ass='{ass_escaped}'"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        output_video
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-3000:]}")


def process_multi_crazy_clips(
    url: str,
    num_clips: int = 5,
    clip_duration: int = 45,
    preset_choice: str = "0",
    cam_pos_choice: str = "1"
):
    print("\n" + "=" * 65)
    print("🎮 YouTube Gaming Crazy Moments Multi-Clipper")
    print("   - 9:16 Fullscreen Gameplay")
    print("   - Tight Fit Gamer Cam (Top-Right Corner, NO Box, NO Empty Space)")
    print("   - Cinematic Spoken Dialogue Captions (Gamer Speech)")
    print(f"   - Detecting Top {num_clips} Crazy Moments")
    print("=" * 65)
    print(f"🔗 Analyzing: {url}")

    info = get_video_info(url)
    title = info.get("title", "Gaming Stream")
    uploader = info.get("uploader", "")
    duration = info.get("duration", 0)
    safe_title = sanitize_filename(title)[:28]

    print(f"📺 Title: {title}")
    if uploader:
        print(f"👤 Channel: {uploader}")
    print(f"⏱ Total Length: {format_time(duration)}")

    pos_map = {
        "1": "right-corner",
        "2": "left-corner",
        "3": "top-center",
        "4": "bottom-right",
        "5": "bottom-left"
    }
    cam_position = pos_map.get(cam_pos_choice, "right-corner")

    print(f"\n🔍 Detecting Top {num_clips} Crazy Moments (Audience Replay Spikes)...")
    clips = find_crazy_moments(info, num_clips=num_clips, clip_duration=clip_duration)

    print(f"\n✨ Selected {len(clips)} Crazy Moments:")
    for idx, c in enumerate(clips, 1):
        print(f"   [{idx}] {format_time(c['start_time'])} ➔ {format_time(c['end_time'])} | {c['reason']}")

    generated_files = []

    for idx, c in enumerate(clips, 1):
        s_time = c["start_time"]
        e_time = c["end_time"]
        s_label = format_time(s_time).replace(":", "m") + "s"

        raw_temp = str(TEMP_DIR / f"raw_clip_{idx}.mp4")
        ass_temp = TEMP_DIR / f"subs_clip_{idx}.ass"
        final_output = str(OUTPUT_DIR / f"{safe_title}_CrazyClip{idx}_{s_label}_9x16.mp4")

        print(f"\n🎬 Clip {idx}/{len(clips)}: [{format_time(s_time)} - {format_time(e_time)}]")
        print("   ⬇ Downloading HD slice...")
        download_clip_section(url, s_time, e_time, raw_temp)

        if not os.path.exists(raw_temp):
            candidates = list(TEMP_DIR.glob(f"raw_clip_{idx}*"))
            if candidates:
                raw_temp = str(candidates[0])
            else:
                print(f"   ⚠️ Could not download segment for Clip {idx}.")
                continue

        # Detect or get camera crop
        crop_filter, cam_w, cam_h = get_cam_filter_and_scale(preset_choice, raw_temp)

        print("   🎙 Extracting Gamer's Spoken Dialogues...")
        dialogues = fetch_spoken_subtitles(url, s_time, e_time)
        generate_cinematic_ass(dialogues, ass_temp)

        if crop_filter:
            print(f"   🎨 Rendering 9:16 + Gamer Cam ({cam_w}×{cam_h} at {cam_position}) + Captions...")
        else:
            print("   🎨 Rendering Fullscreen 9:16 Gameplay + Captions...")

        render_pip_clip(
            input_video=raw_temp,
            output_video=final_output,
            ass_path=ass_temp,
            crop_filter=crop_filter,
            cam_scale_w=cam_w,
            cam_scale_h=cam_h,
            cam_position=cam_position
        )

        # Cleanup temp
        try:
            if os.path.exists(raw_temp):
                os.remove(raw_temp)
            if ass_temp.exists():
                ass_temp.unlink()
        except Exception:
            pass

        print(f"   ✅ Saved: {Path(final_output).name}")
        generated_files.append(final_output)

    print("\n" + "=" * 65)
    print(f"🎉 {len(generated_files)} CRAZY CLIPS GENERATED!")
    print(f"📁 Output Folder: {OUTPUT_DIR}")
    for idx, f in enumerate(generated_files, 1):
        print(f"   {idx}. {Path(f).name}")
    print("=" * 65 + "\n")
    return generated_files


if __name__ == "__main__":
    url_input = ""
    if len(sys.argv) > 1:
        url_input = sys.argv[1]
    else:
        print("\n" + "=" * 65)
        print("🎮 YouTube Gaming Crazy Moments Multi-Clipper")
        print("   - 9:16 Fullscreen Gameplay")
        print("   - Top-Right Gamer Facecam (Tight Fit, NO Box)")
        print("   - Spoken Subtitles (TikTok/Reels Style)")
        print("=" * 65)
        url_input = input("\n👉 Paste YouTube Video / Stream URL: ").strip()

    if not url_input:
        print("❌ Error: No URL provided.")
        sys.exit(1)

    print("\n⚙️ Settings (Press Enter to use defaults):")
    try:
        num_str = input("How many crazy clips do you want? (default: 5): ").strip()
        num_clips = int(num_str) if num_str else 5
    except ValueError:
        num_clips = 5

    try:
        dur_str = input("Clip duration in seconds? (default: 45): ").strip()
        clip_dur = int(dur_str) if dur_str else 45
    except ValueError:
        clip_dur = 45

    print("\n📷 Streamer Facecam Option:")
    for k, v in CALIBRATED_PRESETS.items():
        tag = " [RECOMMENDED - AI Face Detector]" if k == "0" else ""
        print(f"  [{k}] {v['name']}{tag}")

    preset_choice = input("Enter 0–5 (default: 0 - AI Auto-Detect): ").strip()
    if not preset_choice or preset_choice not in CALIBRATED_PRESETS:
        preset_choice = "0"

    print("\n📍 Where should Gamer Cam appear in 9:16 Video?")
    print("  [1] Top-Right Corner [Recommended & Default]")
    print("  [2] Top-Left Corner")
    print("  [3] Top Center")
    print("  [4] Bottom Right")
    print("  [5] Bottom Left")

    pos_choice = input("Enter 1–5 (default: 1 - Top-Right Corner): ").strip()
    if not pos_choice:
        pos_choice = "1"

    process_multi_crazy_clips(
        url=url_input,
        num_clips=num_clips,
        clip_duration=clip_dur,
        preset_choice=preset_choice,
        cam_pos_choice=pos_choice
    )
