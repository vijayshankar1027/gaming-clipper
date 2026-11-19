import os
import sys
import threading
import time
import json
import socket
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_from_directory

# Import our battle-tested clipper functions
from clipper import (
    BASE_DIR, OUTPUT_DIR, TEMP_DIR,
    get_video_info, find_crazy_moments, download_clip_section,
    fetch_spoken_subtitles, generate_cinematic_ass,
    get_cam_filter_and_scale, render_pip_clip,
    sanitize_filename, format_time
)

app = Flask(__name__)

# Global state to track background progress
clipper_status = {
    "is_running": False,
    "progress": 0,
    "current_step": "Ready",
    "total_clips": 0,
    "completed_clips": 0,
    "current_clip_title": "",
    "generated_clips": [],
    "error": None
}


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def background_clipper_task(url, num_clips, clip_dur, preset_choice, cam_pos_choice):
    global clipper_status
    clipper_status["is_running"] = True
    clipper_status["progress"] = 5
    clipper_status["current_step"] = "YouTube Video Analyze ho rahi hai..."
    clipper_status["error"] = None
    clipper_status["total_clips"] = num_clips
    clipper_status["completed_clips"] = 0

    try:
        info = get_video_info(url)
        title = info.get("title", "Gaming Video")
        clipper_status["current_clip_title"] = title
        safe_title = sanitize_filename(title)[:25]

        clipper_status["progress"] = 15
        clipper_status["current_step"] = f"Top {num_clips} Crazy Moments dhoondhe ja rahe hain..."

        clips = find_crazy_moments(info, num_clips=num_clips, clip_duration=clip_dur)
        if not clips:
            clipper_status["error"] = "Koi crazy moment nahi mila."
            clipper_status["is_running"] = False
            return

        total = len(clips)
        clipper_status["total_clips"] = total

        for idx, c in enumerate(clips, 1):
            s_time = c["start_time"]
            e_time = c["end_time"]
            s_label = format_time(s_time).replace(":", "m") + "s"

            base_progress = 20 + int((idx - 1) * (75 / total))

            # Step 1: Downloading slice
            clipper_status["progress"] = base_progress + 5
            clipper_status["current_step"] = f"Clip {idx}/{total}: HD Video Slice Download ho rahi hai..."

            raw_temp = str(TEMP_DIR / f"raw_web_{idx}_{int(time.time())}.mp4")
            ass_temp = TEMP_DIR / f"subs_web_{idx}_{int(time.time())}.ass"
            final_filename = f"{safe_title}_Clip{idx}_{s_label}_9x16.mp4"
            final_output = str(OUTPUT_DIR / final_filename)

            download_clip_section(url, s_time, e_time, raw_temp)

            if not os.path.exists(raw_temp):
                candidates = list(TEMP_DIR.glob(f"raw_web_{idx}*"))
                if candidates:
                    raw_temp = str(candidates[0])
                else:
                    continue

            # Step 2: Camera detect & Subtitles
            clipper_status["progress"] = base_progress + 12
            clipper_status["current_step"] = f"Clip {idx}/{total}: Gamer Facecam & Subtitles process ho rahe hain..."

            crop_filter, cam_w, cam_h = get_cam_filter_and_scale(preset_choice, raw_temp)
            dialogues = fetch_spoken_subtitles(url, s_time, e_time)
            generate_cinematic_ass(dialogues, ass_temp)

            # Step 3: Render 9:16
            clipper_status["progress"] = base_progress + 18
            clipper_status["current_step"] = f"Clip {idx}/{total}: 9:16 Vertical Reel Render ho rahi hai..."

            pos_map = {
                "1": "right-corner",
                "2": "left-corner",
                "3": "top-center"
            }
            cam_pos = pos_map.get(cam_pos_choice, "right-corner")

            render_pip_clip(
                input_video=raw_temp,
                output_video=final_output,
                ass_path=ass_temp,
                crop_filter=crop_filter,
                cam_scale_w=cam_w,
                cam_scale_h=cam_h,
                cam_position=cam_pos
            )

            # Cleanup temp
            for p in [raw_temp, str(ass_temp)]:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

            clipper_status["completed_clips"] = idx
            if final_filename not in clipper_status["generated_clips"]:
                clipper_status["generated_clips"].insert(0, final_filename)

        clipper_status["progress"] = 100
        clipper_status["current_step"] = "🎉 Saari Clips Taiyaar Hain!"

    except Exception as e:
        clipper_status["error"] = str(e)
    finally:
        clipper_status["is_running"] = False


HTML_PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>⚡ Auto Gaming Clipper - 9:16 Viral Shorts</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        body {
            background: #0d0f17;
            color: #fff;
            padding: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            width: 100%;
            max-width: 520px;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px 10px;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #ff007f, #7928ca, #00f2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p {
            font-size: 13px;
            color: #8c93a8;
            margin-top: 5px;
        }
        .card {
            background: #161926;
            border: 1px solid #23283b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        }
        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #b5bdd4;
            margin-bottom: 6px;
        }
        .input-box {
            width: 100%;
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid #2e344e;
            background: #0d0f17;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: border 0.3s;
        }
        .input-box:focus {
            border-color: #00f2fe;
            box-shadow: 0 0 10px rgba(0,242,254,0.2);
        }
        .row-options {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .row-options .input-group {
            flex: 1;
            margin-bottom: 0;
        }
        select.input-box {
            appearance: none;
            cursor: pointer;
        }
        .btn-start {
            width: 100%;
            padding: 16px;
            border-radius: 14px;
            border: none;
            background: linear-gradient(135deg, #ff007f, #7928ca);
            color: white;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(255, 0, 127, 0.4);
            transition: transform 0.2s, opacity 0.2s;
        }
        .btn-start:active {
            transform: scale(0.98);
        }
        .btn-start:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        /* Progress Box */
        .progress-box {
            display: none;
            margin-top: 15px;
            background: #111420;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #23283b;
        }
        .progress-bar-bg {
            width: 100%;
            height: 10px;
            background: #23283b;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #ff007f, #00f2fe);
            border-radius: 10px;
            transition: width 0.4s;
        }
        .status-text {
            font-size: 13px;
            color: #00f2fe;
            font-weight: 600;
        }
        /* Clips Gallery */
        .gallery-title {
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .clip-card {
            background: #161926;
            border: 1px solid #23283b;
            border-radius: 16px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .clip-video {
            width: 100%;
            max-height: 480px;
            background: #000;
            display: block;
        }
        .clip-info {
            padding: 14px;
        }
        .clip-name {
            font-size: 13px;
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 10px;
            word-break: break-all;
        }
        .btn-download {
            display: block;
            width: 100%;
            padding: 12px;
            background: #22c55e;
            color: #000;
            font-weight: 700;
            font-size: 14px;
            text-align: center;
            border-radius: 10px;
            text-decoration: none;
            transition: background 0.2s;
        }
        .btn-download:active {
            background: #16a34a;
        }
        .badge {
            background: rgba(0, 242, 254, 0.15);
            color: #00f2fe;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 9:16 Viral Gaming Clipper</h1>
            <p>Phone ya PC se seedhe YouTube Clips banayein</p>
        </div>

        <div class="card">
            <div class="input-group">
                <label>👉 YouTube Video / Stream Link:</label>
                <input type="text" id="videoUrl" class="input-box" placeholder="https://www.youtube.com/watch?v=...">
            </div>

            <div class="row-options">
                <div class="input-group">
                    <label>Kitne Clips:</label>
                    <select id="numClips" class="input-box">
                        <option value="3">3 Clips</option>
                        <option value="5" selected>5 Clips (Best)</option>
                        <option value="8">8 Clips</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>Duration:</label>
                    <select id="clipDuration" class="input-box">
                        <option value="30">30 Sec (Shorts)</option>
                        <option value="45" selected>45 Sec (Viral)</option>
                        <option value="60">60 Sec (Full)</option>
                    </select>
                </div>
            </div>

            <div class="input-group">
                <label>📷 Gamer Camera Setup:</label>
                <select id="camPreset" class="input-box">
                    <option value="0" selected>🤖 AI Auto-Detect (Face & Reaction Scanner)</option>
                    <option value="1">Top-Right Cam (Dattrax / GTA 6 Streamers)</option>
                    <option value="2">Mid-Left Cam (CarryMinati / Scout)</option>
                    <option value="3">Bottom-Right Cam (Techno Gamerz / Total Gaming)</option>
                    <option value="4">Bottom-Left Cam (Mythpat / Mortal)</option>
                    <option value="5">🚫 No Camera (Gameplay Only)</option>
                </select>
            </div>

            <button id="startBtn" class="btn-start" onclick="startClipping()">
                🚀 Generate Viral 9:16 Clips
            </button>

            <div id="progressBox" class="progress-box">
                <div class="status-text" id="statusText">Starting...</div>
                <div class="progress-bar-bg">
                    <div id="progressBar" class="progress-bar-fill"></div>
                </div>
            </div>
        </div>

        <div class="gallery-title">
            <span>📁 Generated Clips Gallery</span>
            <span class="badge" id="clipCount">0 Clips</span>
        </div>

        <div id="clipsGallery">
            <!-- Dynamically populated -->
        </div>
    </div>

    <script>
        function checkStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const startBtn = document.getElementById('startBtn');
                    const progressBox = document.getElementById('progressBox');
                    const statusText = document.getElementById('statusText');
                    const progressBar = document.getElementById('progressBar');

                    if (data.is_running) {
                        progressBox.style.display = 'block';
                        startBtn.disabled = true;
                        startBtn.innerText = '⏳ Processing Clips...';
                        statusText.innerText = data.current_step + ' (' + data.progress + '%)';
                        progressBar.style.width = data.progress + '%';
                    } else {
                        startBtn.disabled = false;
                        startBtn.innerText = '🚀 Generate Viral 9:16 Clips';
                        if (data.progress === 100) {
                            statusText.innerText = '🎉 ' + data.current_step;
                            progressBar.style.width = '100%';
                        } else if (data.error) {
                            statusText.innerText = '❌ Error: ' + data.error;
                        }
                    }

                    renderClips(data.generated_clips);
                });
        }

        function startClipping() {
            const url = document.getElementById('videoUrl').value.trim();
            if (!url) {
                alert('Bhai, pehle YouTube URL paste karo!');
                return;
            }

            const numClips = document.getElementById('numClips').value;
            const clipDur = document.getElementById('clipDuration').value;
            const camPreset = document.getElementById('camPreset').value;

            document.getElementById('progressBox').style.display = 'block';
            document.getElementById('statusText').innerText = 'Initializing...';
            document.getElementById('progressBar').style.width = '5%';

            fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    num_clips: parseInt(numClips),
                    clip_dur: parseInt(clipDur),
                    cam_preset: camPreset,
                    cam_pos: '1'
                })
            }).then(r => r.json()).then(res => {
                if (res.error) {
                    alert('Error: ' + res.error);
                }
            });
        }

        let renderedList = [];
        function renderClips(clips) {
            document.getElementById('clipCount').innerText = clips.length + ' Clips';
            if (JSON.stringify(clips) === JSON.stringify(renderedList)) return;
            renderedList = clips;

            const gallery = document.getElementById('clipsGallery');
            if (clips.length === 0) {
                gallery.innerHTML = '<div style="text-align:center;color:#64748b;padding:30px;font-size:13px;">Abhi koi clip nahi bani hai. Upar link paste karke Generate dabayein!</div>';
                return;
            }

            gallery.innerHTML = clips.map(name => `
                <div class="clip-card">
                    <video class="clip-video" controls playsinline preload="metadata">
                        <source src="/outputs/${encodeURIComponent(name)}" type="video/mp4">
                    </video>
                    <div class="clip-info">
                        <div class="clip-name">📹 ${name}</div>
                        <a href="/outputs/${encodeURIComponent(name)}" download class="btn-download">
                            📥 Phone / PC par Download Karein
                        </a>
                    </div>
                </div>
            `).join('');
        }

        // Poll status every 2 seconds
        setInterval(checkStatus, 2000);
        checkStatus();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/status")
def status():
    # Also discover any existing clips in outputs folder
    all_files = [
        f.name for f in OUTPUT_DIR.glob("*.mp4")
        if not f.name.startswith("temp")
    ]
    all_files.sort(key=lambda x: (OUTPUT_DIR / x).stat().st_mtime, reverse=True)
    clipper_status["generated_clips"] = all_files
    return jsonify(clipper_status)


@app.route("/api/start", methods=["POST"])
def start():
    global clipper_status
    if clipper_status["is_running"]:
        return jsonify({"error": "Pehle se ek processing chal rahi hai. Please wait kijiye."})

    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided."})

    num_clips = data.get("num_clips", 5)
    clip_dur = data.get("clip_dur", 45)
    cam_preset = data.get("cam_preset", "0")
    cam_pos = data.get("cam_pos", "1")

    # Start background thread
    t = threading.Thread(
        target=background_clipper_task,
        args=(url, num_clips, clip_dur, cam_preset, cam_pos),
        daemon=True
    )
    t.start()

    return jsonify({"success": True})


@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(str(OUTPUT_DIR), filename, as_attachment=False)


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 65)
    print("🚀 9:16 AUTO GAMING CLIPPER WEB INTERFACE CHALU HAI!")
    print("=" * 65)
    print(f"💻 Browser URL: http://localhost:{port} ya http://0.0.0.0:{port}")
    print(f"📱 LAN URL: http://{local_ip}:{port}")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
