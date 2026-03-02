"""
Video generation module using Remotion.
Renders React compositions into MP4 videos via the Remotion CLI.
Supports parameterized rendering by passing JSON props.
"""

import os
import json
import uuid
import subprocess
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

IST = timezone(timedelta(hours=5, minutes=30))
VIDEOS_DIR = os.path.join("static", "videos")
REMOTION_ENTRY = os.path.join("remotion", "index.ts")

# Default video settings
DEFAULT_FPS = 30
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1080


def _ensure_output_dir():
    """Ensure the videos output directory exists."""
    os.makedirs(VIDEOS_DIR, exist_ok=True)


def _generate_video_id():
    """Generate a unique video ID with timestamp."""
    timestamp = datetime.now(IST).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"vid-{timestamp}-{short_uuid}"


def _log(msg):
    """Print a log message with IST timestamp."""
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"[{ts}] [VideoGen] {msg}", flush=True)


def is_enabled():
    """Check if video generation is enabled via env flag."""
    return os.environ.get("ENABLE_VIDEO_GENERATION", "").lower() in ("true", "1", "yes")


def generate_video(composition_id, props=None, duration_seconds=12):
    """
    Render a Remotion composition to an MP4 video.

    Args:
        composition_id: The Remotion composition ID (e.g., 'FunFact', 'OnDemandVideo')
        props: Dictionary of input props to pass to the composition
        duration_seconds: Video duration in seconds (default 12)

    Returns:
        dict with 'video_path', 'video_id' on success.
        None on failure.
    """
    if not is_enabled():
        _log("Video generation is disabled (ENABLE_VIDEO_GENERATION != true)")
        return None

    _ensure_output_dir()

    video_id = _generate_video_id()
    filename = f"{video_id}.mp4"
    output_path = os.path.join(VIDEOS_DIR, filename)

    _log(f"Rendering composition '{composition_id}' → {output_path}")

    # Build the Remotion CLI command
    cmd = [
        "npx", "remotion", "render",
        REMOTION_ENTRY,
        composition_id,
        output_path,
    ]

    # Pass input props as JSON
    if props:
        props_json = json.dumps(props)
        cmd.extend(["--props", props_json])

    _log(f"Command: {' '.join(cmd[:6])}... (props omitted)")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        if result.returncode != 0:
            _log(f"Render failed (exit {result.returncode})")
            _log(f"STDERR: {result.stderr[-500:]}" if result.stderr else "No stderr")
            return None

        if not os.path.exists(output_path):
            _log("Render completed but output file not found!")
            return None

        file_size = os.path.getsize(output_path)
        _log(f"Render complete: {output_path} ({file_size:,} bytes)")

        return {
            "video_id": video_id,
            "video_path": output_path,
            "video_url": f"/video/{video_id}",
        }

    except subprocess.TimeoutExpired:
        _log("Render timed out (180s limit)")
        return None
    except FileNotFoundError:
        _log("npx/remotion not found — is Node.js installed?")
        return None
    except Exception as e:
        _log(f"Render error: {e}")
        return None


def generate_fun_fact_video(fact_text, emoji="🧠"):
    """
    Generate an animated Fun Fact video.

    Args:
        fact_text: The fun fact text content
        emoji: Emoji to display (default: 🧠)

    Returns:
        dict with video_path/video_id on success, None on failure.
    """
    props = {
        "factText": fact_text,
        "emoji": emoji,
        "brandName": "Sparktoship",
    }
    return generate_video("FunFact", props=props, duration_seconds=12)


def generate_on_demand_video(title, content, emoji="✨", style="facts"):
    """
    Generate an on-demand video from user-provided content.

    Args:
        title: Video title/heading
        content: Main text content
        emoji: Display emoji (default: ✨)
        style: Visual style — 'facts', 'explainer', or 'quote'

    Returns:
        dict with video_path/video_id on success, None on failure.
    """
    props = {
        "title": title,
        "content": content,
        "emoji": emoji,
        "brandName": "Sparktoship",
        "style": style,
    }
    return generate_video("OnDemandVideo", props=props, duration_seconds=12)


def cleanup_old_videos(max_age_hours=24):
    """Remove video files older than max_age_hours."""
    if not os.path.exists(VIDEOS_DIR):
        return

    now = datetime.now(IST)
    removed = 0

    for f in os.listdir(VIDEOS_DIR):
        if not f.endswith(".mp4"):
            continue
        filepath = os.path.join(VIDEOS_DIR, f)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=IST)
            age_hours = (now - mtime).total_seconds() / 3600
            if age_hours > max_age_hours:
                os.remove(filepath)
                removed += 1
        except Exception:
            pass

    if removed:
        _log(f"Cleaned up {removed} old video(s)")
