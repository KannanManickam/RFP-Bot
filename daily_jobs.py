"""
Daily scheduled jobs for Telegram bot.
Job 1: Fun Fact — interesting trivia + AI-generated illustration
Job 2: Tech Pulse — two prompts based on time of day:
        • Morning (before 2 PM IST): AI Tech Pulse — trending AI news + build ideas
        • Evening (2 PM IST onwards): Drone & IoT Pulse — drones, IoT, robotics trends

Schedule is configurable via env vars:
  SCHEDULE_START_HOUR  — first run hour  (default 10)
  SCHEDULE_END_HOUR    — last run hour   (default 22)
  SCHEDULE_INTERVAL_HOURS — gap between runs (default 4)
"""

import os
import io
import traceback
from datetime import datetime, timezone, timedelta

from openai import OpenAI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from image_generator import generate_image_from_text
from video_generator import generate_fun_fact_video, is_enabled as video_enabled, cleanup_old_videos
from content_history import (
    get_recent_topics,
    add_entry,
    pick_fresh_category,
)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

IST = timezone(timedelta(hours=5, minutes=30))

client_ai = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
)

CONTENT_MODEL = "gpt-5-nano"
CHAT_ID = None  # Set at startup via init()


def _log(msg):
    """Print a log message with IST timestamp."""
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"[{ts}] [DailyJobs] {msg}", flush=True)
_bot = None     # Telegram bot instance, set at startup via init()


# ─────────────────────────────────────────────
# Job 1: Daily Fun Fact
# ─────────────────────────────────────────────

import json as _json

FUN_FACT_SYSTEM_PROMPT = (
    "You are a world-class trivia curator known for jaw-dropping, obscure facts "
    "that make people stop scrolling and say 'wait, WHAT?!'\n\n"
    "RULES:\n"
    "- Generate ONE fun fact from the SPECIFIC CATEGORY given to you. "
    "Stick strictly to that category.\n"
    "- The fact must be TRUE and verifiable.\n"
    "- Pick something genuinely surprising — avoid well-known trivia. "
    "Go deep and obscure.\n"
    "- Write in a conversational, engaging tone. 30 to 50 words maximum for factText — no more.\n"
    "- Start with the mind-blowing hook, then the backstory.\n"
    "- End with a fun closing remark or emoji.\n"
    "- Do NOT use a title or heading — just the text.\n"
    "- Do NOT repeat common facts (e.g., 'honey never expires', "
    "'octopuses have three hearts', 'bananas are berries').\n"
    "- Be WILDLY creative. Surprise me.\n\n"
    "RESPONSE FORMAT — return a JSON object with exactly these four keys:\n"
    "  factText   : the fun fact (30–50 words max)\n"
    "  emoji      : a single emoji that best represents the fact\n"
    "  hookLine   : a punchy teaser of 5–8 words (e.g. 'Did you know flamingos are born white?')\n"
    "  sourceLabel: the knowledge domain or source (e.g. 'Biology', 'NASA', 'Oxford Studies', 'History')\n"
    "Return ONLY the JSON object, no markdown fencing or extra text."
)


def _summarize_content(text: str) -> str:
    """Generate a 1-line summary of content for deduplication tracking."""
    try:
        response = client_ai.chat.completions.create(
            model=CONTENT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following content in exactly ONE short line (max 15 words). "
                    "Capture the core topic/subject only. No fluff.",
                },
                {"role": "user", "content": text[:500]},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Fallback: use first 80 chars of the content itself
        return text[:80].replace("\n", " ")


def _generate_fun_fact_text():
    """Generate a fun fact via AI. Returns dict: factText, emoji, hookLine, sourceLabel."""
    today = datetime.now(IST).strftime("%A, %d %B %Y")

    category = pick_fresh_category()
    _log(f"Fun fact category: {category}")

    recent_topics = get_recent_topics("fun_fact", limit=30)
    anti_repeat = ""
    if recent_topics:
        topics_list = "\n".join(f"- {t}" for t in recent_topics)
        anti_repeat = (
            f"\n\nCRITICAL — DO NOT cover any of these previously sent topics:\n"
            f"{topics_list}\n\nPick something completely different."
        )

    response = client_ai.chat.completions.create(
        model=CONTENT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": FUN_FACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Today is {today}.\n"
                    f"YOUR CATEGORY: {category}\n\n"
                    f"Generate a fresh, surprising fun fact from the "
                    f"'{category}' category that I probably haven't heard before."
                    f"{anti_repeat}"
                ),
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    try:
        data = _json.loads(raw)
        fact_text    = data.get("factText", raw)
        emoji        = data.get("emoji", "🧠")
        hook_line    = data.get("hookLine", "")
        source_label = data.get("sourceLabel", "")
    except Exception:
        _log("Warning: could not parse JSON from AI, using raw text")
        fact_text    = raw
        emoji        = "🧠"
        hook_line    = ""
        source_label = ""

    summary = _summarize_content(fact_text)
    add_entry("fun_fact", summary, category=category)
    _log(f"Fun fact tracked: [{category}] {summary}")

    return {
        "factText": fact_text,
        "emoji": emoji,
        "hookLine": hook_line,
        "sourceLabel": source_label,
    }


def run_fun_fact_job(chain=True):
    """Execute the Fun Fact job: generate text + image, send to Telegram.
    If chain=True (default for scheduled runs), AI Tech Pulse runs immediately after.
    """
    if not _bot or not CHAT_ID:
        _log("Fun Fact skipped — bot or CHAT_ID not configured.")
        return

    _log("Running Fun Fact job...")

    try:
        # 1. Generate the fun fact (returns dict: factText, emoji, hookLine, sourceLabel)
        fact_data    = _generate_fun_fact_text()
        fact_text    = fact_data["factText"]
        emoji        = fact_data["emoji"]
        hook_line    = fact_data.get("hookLine", "")
        source_label = fact_data.get("sourceLabel", "")
        _log(f"Fun fact generated ({len(fact_text)} chars) | hook: '{hook_line}' | source: '{source_label}'")

        # 2. Send the text message first
        header = "🧠 *Daily Fun Fact*\n\n"
        _bot.send_message(CHAT_ID, header + fact_text, parse_mode="Markdown")

        # 3. Generate an illustrative image
        image_prompt = f"A colorful, whimsical illustration of this fun fact: {fact_text[:300]}"
        result = generate_image_from_text(image_prompt, size="1024x1024", quality="low")

        if result and result.get("image_path"):
            _send_image(CHAT_ID, result["image_path"], caption="🎨 _Illustration of today's fun fact_")
        else:
            _log("Image generation failed, sending text only.")

        # 4. Generate animated video (if enabled)
        if video_enabled():
            _log("Generating Fun Fact video...")
            bg_image_path = result.get("image_path") if result else None
            video_result = generate_fun_fact_video(
                fact_text,
                emoji=emoji,
                image_path=bg_image_path,
                hook_line=hook_line,
                source_label=source_label,
            )
            if video_result and video_result.get("video_path"):
                _send_video(CHAT_ID, video_result["video_path"], caption="🎬 _Animated fun fact_")
            else:
                _log("Video generation failed, skipping.")

            # Periodic cleanup of old videos
            cleanup_old_videos(max_age_hours=48)

        _log("Fun Fact job completed.")

    except Exception as e:
        _log(f"Fun Fact job error: {e}")
        traceback.print_exc()

    # Chain: run AI Tech Pulse immediately after Fun Fact
    if chain:
        _log("Chaining → AI Tech Pulse...")
        run_ai_tech_pulse_job()


# ─────────────────────────────────────────────
# Job 2: AI Tech Pulse
# ─────────────────────────────────────────────

AI_TECH_PULSE_SYSTEM_PROMPT = (
    "You are a VIRAL AI tech scout for a product manager who is also a developer "
    "and builder. Your job is to surface the most EXCITING, buzz-worthy things "
    "happening in AI RIGHT NOW — the stuff that's blowing up on Twitter/X, "
    "Hacker News, Reddit r/LocalLLaMA, and the builder community.\n\n"
    "RULES:\n"
    "- Focus on VIRAL moments: things like OpenClaw, Perplexity Computer, "
    "new model drops that broke the internet, viral GitHub repos with 1000+ "
    "stars overnight, game-changing API launches, open-source projects that "
    "went viral, breakthrough demos that made devs say 'I need to build with this'.\n"
    "- Target audience is a BUILDER — they want things they can try, fork, "
    "build on top of, or integrate into their projects.\n"
    "- Be SPECIFIC: name the repo, the tool, the model, the API. No vague "
    "generalizations like 'AI is transforming healthcare'.\n"
    "- SKIP: company earnings, funding rounds, corporate drama, lawsuits, "
    "regulatory news, generic think-pieces.\n"
    "- Each trend should make the reader think: 'I need to check this out "
    "RIGHT NOW and maybe build something with it.'\n\n"
    "FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:\n\n"
    "📡 What's Viral in AI Right Now\n\n"
    "[2-3 trends, each with an emoji number (1️⃣ 2️⃣ 3️⃣), a bold title, "
    "and 2-3 lines on what it is, why it went viral, and why a builder should care]\n\n"
    "🛠 Build Ideas\n\n"
    "[2-3 actionable project ideas inspired by the trends above. "
    "Each starts with 💡 and is 1-2 lines. These should be things a solo "
    "developer or small team could actually build THIS WEEKEND.]\n\n"
    "📊 Quick Stat\n\n"
    "[One mind-blowing AI stat or metric from this week.]\n\n"
    "Keep the entire response concise, punchy, and exciting. Use emojis tastefully. "
    "Do NOT use markdown headers (#). Use plain text with emoji separators."
)

EVENING_TECH_PULSE_SYSTEM_PROMPT = (
    "You are a tech trends curator for someone who RUNS A STEM EDUCATION CENTER "
    "IN INDIA, teaching students how to BUILD drones, robotics projects, and IoT "
    "systems. Your job is to surface the most exciting, student-relevant "
    "developments in these spaces.\n\n"
    "CONTEXT ABOUT THE AUDIENCE:\n"
    "- Runs a hands-on STEM center in India for students\n"
    "- Teaches drone building, robotics, and IoT\n"
    "- Interested in things students can actually BUILD and LEARN from\n"
    "- Cares about affordable hardware, open-source projects, and Indian ecosystem\n\n"
    "RULES:\n"
    "- Focus on: student-buildable drone projects, affordable robotics kits, "
    "open-source drone frames (ArduPilot, PX4, Betaflight), IoT projects with "
    "ESP32/Arduino/Raspberry Pi, ROS/ROS2 tutorials and projects, Indian drone "
    "regulations (DGCA updates), Indian competitions (e-Yantra, Smart India "
    "Hackathon, Drone Olympics), Indian maker community highlights.\n"
    "- Every trend should answer: 'What can my students BUILD from this?'\n"
    "- Include India-specific context: pricing in INR where relevant, "
    "availability in India, relevance to Indian STEM education.\n"
    "- SKIP: military drones, enterprise-only solutions students can't access, "
    "generic industry reports, corporate funding news.\n"
    "- Be specific with hardware names, project repos, competition details.\n\n"
    "FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:\n\n"
    "🚁 STEM Builder Pulse — Drones, Robotics & IoT\n\n"
    "[2-3 trends, each with an emoji number (1️⃣ 2️⃣ 3️⃣), a bold title, "
    "and 2-3 lines on what it is and how students/makers can use it]\n\n"
    "🛠 Student Project Ideas\n\n"
    "[2-3 hands-on project ideas students could build, inspired by the trends. "
    "Each starts with 💡 and is 1-2 lines. Include approximate cost in INR "
    "if hardware is involved.]\n\n"
    "📊 Quick Stat\n\n"
    "[One interesting stat about drones/robotics/IoT in India or globally.]\n\n"
    "Keep the entire response concise, exciting, and actionable for educators "
    "and student builders. Use emojis tastefully. "
    "Do NOT use markdown headers (#). Use plain text with emoji separators."
)


def _is_morning():
    """Return True if current IST hour is before 14:00 (2 PM)."""
    return datetime.now(IST).hour < 14


def _generate_ai_tech_pulse(morning=True):
    """Generate tech trending content using AI with anti-repeat.
    morning=True  → AI Tech Pulse (viral AI for builders)
    morning=False → STEM Builder Pulse (drones, IoT, robotics for India STEM center)
    """
    today = datetime.now(IST).strftime("%A, %d %B %Y")
    content_type = "ai_tech_pulse" if morning else "drone_iot_pulse"

    # Build anti-repeat context
    recent_topics = get_recent_topics(content_type, limit=30)
    anti_repeat = ""
    if recent_topics:
        topics_list = "\n".join(f"- {t}" for t in recent_topics)
        anti_repeat = (
            f"\n\nCRITICAL — DO NOT cover any of these previously sent topics:\n"
            f"{topics_list}\n\nCover something completely NEW."
        )

    if morning:
        system_prompt = AI_TECH_PULSE_SYSTEM_PROMPT
        user_msg = (
            f"Today is {today}. What are the most VIRAL and exciting things "
            "happening in AI right now? I want the stuff that's blowing up on "
            "Twitter/X and Hacker News — things I can try, build with, or fork. "
            "Think: new model drops, viral repos, game-changing tools, community "
            f"projects that went big.{anti_repeat}"
        )
    else:
        system_prompt = EVENING_TECH_PULSE_SYSTEM_PROMPT
        user_msg = (
            f"Today is {today}. What are the most exciting developments in "
            "drones, IoT, and robotics that my STEM students in India would "
            "love? Focus on things they can BUILD — affordable hardware, "
            "open-source projects, new drone frames, robotics kits, IoT boards, "
            "Indian competitions, and maker community highlights. "
            f"Make it actionable for educators and student builders.{anti_repeat}"
        )

    response = client_ai.chat.completions.create(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    content = response.choices[0].message.content.strip()

    # Track in history
    summary = _summarize_content(content)
    add_entry(content_type, summary)
    _log(f"{content_type} tracked: {summary}")

    return content


def run_ai_tech_pulse_job():
    """Execute the Tech Pulse job.
    Automatically selects morning (AI Tech) or evening (Drone & IoT) prompt
    based on the current IST hour.
    """
    if not _bot or not CHAT_ID:
        _log("Tech Pulse skipped — bot or CHAT_ID not configured.")
        return

    morning = _is_morning()
    variant = "AI Tech Pulse" if morning else "Drone & IoT Pulse"
    _log(f"Running {variant} job...")

    try:
        today = datetime.now(IST).strftime("%d %b %Y")
        content = _generate_ai_tech_pulse(morning=morning)
        _log(f"{variant} generated ({len(content)} chars)")

        if morning:
            header = f"🔥 *AI Tech Pulse — {today}*\n\n━━━━━━━━━━━━━━━━━━━━\n"
        else:
            header = f"🚁 *STEM Builder Pulse — {today}*\n\n━━━━━━━━━━━━━━━━━━━━\n"

        full_message = header + content

        # Telegram has a 4096 char limit per message
        if len(full_message) > 4096:
            _send_long_message(CHAT_ID, full_message)
        else:
            _bot.send_message(CHAT_ID, full_message, parse_mode="Markdown")

        _log(f"{variant} job completed.")

    except Exception as e:
        _log(f"{variant} job error: {e}")
        traceback.print_exc()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _send_image(chat_id, image_path, caption=""):
    """Send an image to Telegram with compression for fast upload."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        if img.mode == "RGBA":
            img = img.convert("RGB")
        max_side = 1024
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        buf.seek(0)
        buf.name = "funfact.jpg"
        _bot.send_photo(chat_id, buf, caption=caption, parse_mode="Markdown")
    except Exception as e:
        _log(f"Error sending image: {e}")


def _send_video(chat_id, video_path, caption=""):
    """Send a video to Telegram."""
    try:
        with open(video_path, "rb") as vf:
            _bot.send_video(
                chat_id,
                vf,
                caption=caption,
                parse_mode="Markdown",
                supports_streaming=True,
            )
    except Exception as e:
        _log(f"Error sending video: {e}")


def _send_long_message(chat_id, text, max_len=4096):
    """Split and send a long message in chunks."""
    while text:
        if len(text) <= max_len:
            _bot.send_message(chat_id, text, parse_mode="Markdown")
            break
        # Find a good split point (newline before limit)
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        _bot.send_message(chat_id, text[:split_at], parse_mode="Markdown")
        text = text[split_at:].lstrip("\n")


# ─────────────────────────────────────────────
# Scheduler Init
# ─────────────────────────────────────────────

scheduler = None


def _get_schedule_hours():
    """Compute the list of scheduled hours from env configuration."""
    start = int(os.environ.get("SCHEDULE_START_HOUR", "10"))
    end = int(os.environ.get("SCHEDULE_END_HOUR", "22"))
    interval = int(os.environ.get("SCHEDULE_INTERVAL_HOURS", "4"))
    hours = list(range(start, end + 1, interval))
    return hours, start, end, interval


def init(bot_instance):
    """
    Initialize daily jobs with the Telegram bot instance.
    Call this from main.py after bot is ready.
    """
    global _bot, CHAT_ID, scheduler

    _bot = bot_instance
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    if not CHAT_ID:
        _log("WARNING: TELEGRAM_CHAT_ID not set. Scheduled jobs won't send messages.")
        _log("Commands /funfact and /aipulse will still work when triggered from chat.")

    hours, start, end, interval = _get_schedule_hours()
    hour_csv = ",".join(str(h) for h in hours)

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Single cron: Fun Fact fires at :00, then chains AI Tech Pulse immediately after
    scheduler.add_job(
        run_fun_fact_job,
        CronTrigger(hour=hour_csv, minute=0, timezone="Asia/Kolkata"),
        id="daily_scheduled_jobs",
        name="Daily Scheduled Jobs (Fun Fact → AI Tech Pulse)",
        replace_existing=True,
    )

    scheduler.start()
    pretty_hours = ", ".join(f"{h}:00" for h in hours)
    _log(f"Scheduler started — every {interval}h from {start}:00 to {end}:00 IST")
    _log(f"  Scheduled hours : {pretty_hours}")
    _log(f"  • Fun Fact      → runs first")
    _log(f"  • AI Tech Pulse → runs immediately after Fun Fact")


def trigger_fun_fact(chat_id):
    """Manually trigger Fun Fact for a specific chat (used by /funfact command)."""
    global CHAT_ID
    original_chat_id = CHAT_ID
    CHAT_ID = chat_id
    try:
        run_fun_fact_job(chain=False)
    finally:
        CHAT_ID = original_chat_id


def trigger_ai_tech_pulse(chat_id):
    """Manually trigger AI Tech Pulse for a specific chat (used by /aipulse command)."""
    global CHAT_ID
    original_chat_id = CHAT_ID
    CHAT_ID = chat_id
    try:
        run_ai_tech_pulse_job()
    finally:
        CHAT_ID = original_chat_id
