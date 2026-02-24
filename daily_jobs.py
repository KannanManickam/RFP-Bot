"""
Daily scheduled jobs for Telegram bot.
Job 1: Fun Fact (11:00 AM IST) — interesting trivia + AI-generated illustration
Job 2: AI Tech Pulse (11:30 AM IST) — trending AI news + build ideas + LinkedIn suggestions
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
    "- 3 to 6 lines maximum.\n"
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


def run_fun_fact_job():
    """Execute the Fun Fact job: generate text + image, send to Telegram."""
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
    "[3-4 actionable project ideas inspired by the trends above. "
    "Each starts with 💡 and is 1-2 lines. These should be things a solo "
    "developer or small team could actually build.]\n\n"
    "📝 LinkedIn Post Ideas\n\n"
    "[Pick 1-2 of the build ideas above and draft a compelling LinkedIn "
    "post angle/hook for each. Start with 🔹. Include the format suggestion "
    "(thread, hot take, tutorial, etc.)]\n\n"
    "📊 Quick Stat\n\n"
    "[One notable AI stat or metric from this week — can be approximate.]\n\n"
    "Keep the entire response concise and punchy. Use emojis tastefully. "
    "Do NOT use markdown headers (#). Use plain text with emoji separators."
)


def _generate_ai_tech_pulse():
    """Generate AI tech trending content using AI."""
    today = datetime.now(IST).strftime("%A, %d %B %Y")
    response = client_ai.chat.completions.create(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": AI_TECH_PULSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Today is {today}. What are the most viral and trending "
                    "AI tech topics right now? Focus on what developers and "
                    "builders are excited about."
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


def run_ai_tech_pulse_job():
    """Execute the AI Tech Pulse job: generate and send trending AI news."""
    if not _bot or not CHAT_ID:
        _log("AI Tech Pulse skipped — bot or CHAT_ID not configured.")
        return

    _log("Running AI Tech Pulse job...")

    try:
        today = datetime.now(IST).strftime("%d %b %Y")
        content = _generate_ai_tech_pulse()
        _log(f"AI Tech Pulse generated ({len(content)} chars)")

        header = f"🔥 *AI Tech Pulse — {today}*\n\n━━━━━━━━━━━━━━━━━━━━\n"
        full_message = header + content

        # Telegram has a 4096 char limit per message
        if len(full_message) > 4096:
            # Split into chunks at line breaks
            _send_long_message(CHAT_ID, full_message)
        else:
            _bot.send_message(CHAT_ID, full_message, parse_mode="Markdown")

        _log("AI Tech Pulse job completed.")

    except Exception as e:
        _log(f"AI Tech Pulse job error: {e}")
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

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Job 1: Fun Fact at 11:00 AM IST daily
    scheduler.add_job(
        run_fun_fact_job,
        CronTrigger(hour=11, minute=0, timezone="Asia/Kolkata"),
        id="daily_fun_fact",
        name="Daily Fun Fact",
        replace_existing=True,
    )

    # Job 2: AI Tech Pulse at 11:30 AM IST daily
    scheduler.add_job(
        run_ai_tech_pulse_job,
        CronTrigger(hour=11, minute=30, timezone="Asia/Kolkata"),
        id="daily_ai_tech_pulse",
        name="Daily AI Tech Pulse",
        replace_existing=True,
    )

    scheduler.start()
    _log("Scheduler started with 2 jobs:")
    _log("  • Fun Fact       → 11:00 AM IST daily")
    _log("  • AI Tech Pulse  → 11:30 AM IST daily")


def trigger_fun_fact(chat_id):
    """Manually trigger Fun Fact for a specific chat (used by /funfact command)."""
    global CHAT_ID
    original_chat_id = CHAT_ID
    CHAT_ID = chat_id
    try:
        run_fun_fact_job()
    finally:
        CHAT_ID = original_chat_id


def trigger_ai_tech_pulse(chat_id):
    """Manually trigger AI Tech Pulse for a specific chat (used by /aitechpulse command)."""
    global CHAT_ID
    original_chat_id = CHAT_ID
    CHAT_ID = chat_id
    try:
        run_ai_tech_pulse_job()
    finally:
        CHAT_ID = original_chat_id
