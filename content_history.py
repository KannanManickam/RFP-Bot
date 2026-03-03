"""
Content history tracker for deduplication of daily jobs.

Stores recent content summaries in a JSON file so that AI prompts can
avoid repeating previously sent topics.  Each content type (fun_fact,
ai_tech_pulse, drone_iot_pulse) keeps its own rolling window of entries.

File location: /app/data/content_history.json (persisted via Docker volume).
"""

import json
import os
import random
import fcntl
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Configuration ────────────────────────────────────────
HISTORY_DIR = os.environ.get("CONTENT_HISTORY_DIR", os.path.join(os.path.dirname(__file__), "data"))
HISTORY_FILE = os.path.join(HISTORY_DIR, "content_history.json")
MAX_ENTRIES_PER_TYPE = 60

# ── Fun Fact Categories ──────────────────────────────────
FUN_FACT_CATEGORIES = [
    "Sports Records & Origins",
    "Food Origins & Culinary History",
    "Space, Planets & Astronomy",
    "World Geography & Landmarks",
    "Famous People & Hidden Stories",
    "Colors, Light & Optics",
    "Fruits, Plants & Botany",
    "Ocean Life & Marine Wonders",
    "Ancient Civilizations & Empires",
    "Music History & Instruments",
    "Animal Behaviors & Abilities",
    "Inventions & Accidental Discoveries",
    "Languages & Linguistics",
    "Weather Phenomena & Climate",
    "Human Body & Medicine",
    "Architecture & Engineering Marvels",
    "Currencies, Money & Trade",
    "Festivals & Cultural Traditions Worldwide",
    "Optical Illusions & Perception",
    "Mathematical Oddities & Puzzles",
    "Movies, TV & Pop Culture",
    "Transportation & Vehicles",
    "Gems, Minerals & Geology",
    "Fashion & Clothing History",
    "Board Games, Toys & Play",
]


def _ensure_dir():
    """Create the history directory if it doesn't exist."""
    os.makedirs(HISTORY_DIR, exist_ok=True)


def _read_history() -> dict:
    """Read the history file. Returns empty structure if file is missing."""
    _ensure_dir()
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
            return data
    except (json.JSONDecodeError, IOError):
        return {}


def _write_history(data: dict):
    """Write the history file with exclusive lock."""
    _ensure_dir()
    with open(HISTORY_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)


# ── Public API ───────────────────────────────────────────

def get_recent_topics(content_type: str, limit: int = 30) -> list[str]:
    """Return the most recent topic summaries for a content type.

    Args:
        content_type: One of 'fun_fact', 'ai_tech_pulse', 'drone_iot_pulse'.
        limit: Maximum number of topics to return.

    Returns:
        List of topic summary strings (most recent first).
    """
    history = _read_history()
    entries = history.get(content_type, [])
    return [e["topic_summary"] for e in entries[-limit:]][::-1]


def add_entry(content_type: str, topic_summary: str, category: str = ""):
    """Add a new entry to the history for a content type.

    Automatically trims old entries beyond MAX_ENTRIES_PER_TYPE.

    Args:
        content_type: One of 'fun_fact', 'ai_tech_pulse', 'drone_iot_pulse'.
        topic_summary: A 1-line summary of the content that was sent.
        category: Optional category (used for fun facts).
    """
    history = _read_history()
    if content_type not in history:
        history[content_type] = []

    entry = {
        "date": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "topic_summary": topic_summary,
    }
    if category:
        entry["category"] = category

    history[content_type].append(entry)

    # Trim to rolling window
    if len(history[content_type]) > MAX_ENTRIES_PER_TYPE:
        history[content_type] = history[content_type][-MAX_ENTRIES_PER_TYPE:]

    _write_history(history)


def get_recent_categories(limit: int = 10) -> list[str]:
    """Return the most recently used fun fact categories.

    Args:
        limit: Number of recent categories to return.

    Returns:
        List of category strings (most recent first).
    """
    history = _read_history()
    entries = history.get("fun_fact", [])
    categories = [e["category"] for e in entries[-limit:] if e.get("category")]
    return categories[::-1]


def pick_fresh_category() -> str:
    """Pick a fun fact category that hasn't been used in the last 10 runs.

    Falls back to a random choice if all categories have been recently used
    (unlikely with 25 categories and a window of 10).

    Returns:
        A category string.
    """
    recent = set(get_recent_categories(limit=10))
    available = [c for c in FUN_FACT_CATEGORIES if c not in recent]
    if not available:
        # All categories used recently — just pick any random one
        available = FUN_FACT_CATEGORIES
    return random.choice(available)
