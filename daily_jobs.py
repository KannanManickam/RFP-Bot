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

FUN_FACT_SYSTEM_PROMPT = (
    "You are a fascinating trivia curator. Generate ONE interesting, obscure, "
    "and surprising fun fact. Topics can include: etymology, science, history, "
    "sports origins, language quirks, mathematics, nature, food origins, "
    "cultural traditions, or any 'did you know' style knowledge.\n\n"
    "RULES:\n"
    "- The fact must be TRUE and verifiable.\n"
    "- Write in a conversational, engaging tone.\n"
    "- 3 to 5 lines maximum.\n"
    "- Start with the surprising hook, then explain the backstory.\n"
    "- End with a fun closing remark or emoji.\n"
    "- Do NOT use a title or heading — just the text.\n"
    "- Do NOT repeat common facts (e.g., 'honey never expires'). Be creative.\n"
    "- Vary the topic every time — cover different domains."
)


def _generate_fun_fact_text():
    """Generate an interesting fun fact using AI."""
    today = datetime.now(IST).strftime("%A, %d %B %Y")
    response = client_ai.chat.completions.create(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": FUN_FACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Today is {today}. Generate a fresh, surprising fun fact "
                    "that I probably haven't heard before."
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


def run_fun_fact_job(chain=True):
    """Execute the Fun Fact job: generate text + image, send to Telegram.
    If chain=True (default for scheduled runs), AI Tech Pulse runs immediately after.
    """
    if not _bot or not CHAT_ID:
        _log("Fun Fact skipped — bot or CHAT_ID not configured.")
        return

    _log("Running Fun Fact job...")

    try:
        # 1. Generate the fun fact text
        fact_text = _generate_fun_fact_text()
        _log(f"Fun fact generated ({len(fact_text)} chars)")

        # 2. Send the text message first
        header = "🧠 *Daily Fun Fact*\n\n"
        _bot.send_message(CHAT_ID, header + fact_text, parse_mode="Markdown")

        # 3. Generate an illustrative image using gpt-image-1.5
        image_prompt = f"A colorful, whimsical illustration of this fun fact: {fact_text[:300]}"
        result = generate_image_from_text(image_prompt, size="1024x1024", quality="low")

        if result and result.get("image_path"):
            _send_image(CHAT_ID, result["image_path"], caption="🎨 _Illustration of today's fun fact_")
        else:
            _log("Image generation failed, sending text only.")

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
    "You are an AI tech trends curator for a builder/developer audience. "
    "Your job is to identify what's buzzing in the AI tech world RIGHT NOW.\n\n"
    "RULES:\n"
    "- Focus ONLY on AI/ML technology trends — NOT company earnings, politics, "
    "lawsuits, or corporate drama.\n"
    "- Highlight things like: new open-source models, viral GitHub repos, "
    "agentic tools, novel techniques, breakthrough papers, community-built "
    "projects, new frameworks, API launches, or developer tool innovations.\n"
    "- Be specific with names, repos, and tools when possible.\n\n"
    "FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:\n\n"
    "📡 Trending in AI Tech\n\n"
    "[2-3 trends, each with an emoji number (1️⃣ 2️⃣ 3️⃣), a bold title, "
    "and 2-3 lines explaining what's happening and why it matters]\n\n"
    "🛠 Build Ideas\n\n"
    "[2-3 actionable project ideas inspired by the trends above. "
    "Each starts with 💡 and is 1-2 lines. These should be things a solo "
    "developer or small team could actually build.]\n\n"
    "📊 Quick Stat\n\n"
    "[One notable AI stat or metric from this week — can be approximate.]\n\n"
    "Keep the entire response concise and punchy. Use emojis tastefully. "
    "Do NOT use markdown headers (#). Use plain text with emoji separators."
)

EVENING_TECH_PULSE_SYSTEM_PROMPT = (
    "You are a tech trends curator specialising in Drones, IoT, and Robotics "
    "for a builder/developer audience. Your job is to surface what's buzzing "
    "in these domains RIGHT NOW.\n\n"
    "RULES:\n"
    "- Focus ONLY on: drones, UAVs, IoT platforms & protocols, robotics, "
    "embedded AI, edge computing, sensor tech, ROS/ROS2, autonomous systems, "
    "hardware launches, and open-source robotics/IoT projects.\n"
    "- Do NOT cover general AI/ML, company earnings, politics, or corporate drama.\n"
    "- Be specific with product names, repos, frameworks, and hardware when possible.\n\n"
    "FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:\n\n"
    "🚁 Trending in Drones, IoT & Robotics\n\n"
    "[2-3 trends, each with an emoji number (1️⃣ 2️⃣ 3️⃣), a bold title, "
    "and 2-3 lines explaining what's happening and why it matters]\n\n"
    "🛠 Build Ideas\n\n"
    "[2-3 actionable project ideas inspired by the trends above. "
    "Each starts with 💡 and is 1-2 lines. Focus on drone builds, IoT "
    "prototypes, or robotics projects a solo developer or small team could tackle.]\n\n"
    "📊 Quick Stat\n\n"
    "[One notable stat or metric from the drones/IoT/robotics world — "
    "can be approximate.]\n\n"
    "Keep the entire response concise and punchy. Use emojis tastefully. "
    "Do NOT use markdown headers (#). Use plain text with emoji separators."
)


def _is_morning():
    """Return True if current IST hour is before 14:00 (2 PM)."""
    return datetime.now(IST).hour < 14


def _generate_ai_tech_pulse(morning=True):
    """Generate tech trending content using AI.
    morning=True  → AI Tech Pulse (general AI/ML)
    morning=False → Drone & IoT Pulse (drones, IoT, robotics)
    """
    today = datetime.now(IST).strftime("%A, %d %B %Y")

    if morning:
        system_prompt = AI_TECH_PULSE_SYSTEM_PROMPT
        user_msg = (
            f"Today is {today}. What are the most viral and trending "
            "AI tech topics right now? Focus on what developers and "
            "builders are excited about."
        )
    else:
        system_prompt = EVENING_TECH_PULSE_SYSTEM_PROMPT
        user_msg = (
            f"Today is {today}. What are the most exciting developments "
            "in drones, IoT, and robotics right now? Cover new hardware, "
            "open-source projects, frameworks, and anything builders are "
            "buzzing about in these spaces."
        )

    response = client_ai.chat.completions.create(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )
    return response.choices[0].message.content.strip()


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
            header = f"🚁 *Drone & IoT Pulse — {today}*\n\n━━━━━━━━━━━━━━━━━━━━\n"

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
