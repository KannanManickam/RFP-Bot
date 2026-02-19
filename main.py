import os
import re
import time
import threading
import telebot
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, send_from_directory, send_file, render_template_string, abort

from generator import build_proposal, load_proposals_index, MY_BRAND
from document_parser import parse_uploaded_file, fetch_remote_document

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DOMAIN = os.environ.get("APP_DOMAIN", os.environ.get("REPLIT_DEV_DOMAIN", ""))

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False) if TELEGRAM_TOKEN else None

# ─────────────────────────────────────────────
# Session Management
# ─────────────────────────────────────────────

SESSION_TIMEOUT = 30 * 60  # 30 minutes

# Session steps
STEP_AWAITING_CLIENT_INFO = "awaiting_client_info"
STEP_AWAITING_BRIEF = "awaiting_brief"
STEP_AWAITING_CURRENCY = "awaiting_currency"
STEP_AWAITING_SCALE = "awaiting_scale"
STEP_AWAITING_DOCUMENT = "awaiting_document"

user_sessions = {}
sessions_lock = threading.Lock()


def get_session(chat_id):
    """Get or return None for a user session."""
    with sessions_lock:
        session = user_sessions.get(chat_id)
        if session:
            if time.time() - session.get("last_active", 0) > SESSION_TIMEOUT:
                del user_sessions[chat_id]
                return None
            session["last_active"] = time.time()
        return session


def create_session(chat_id):
    """Create a new session for the user."""
    with sessions_lock:
        user_sessions[chat_id] = {
            "step": STEP_AWAITING_CLIENT_INFO,
            "client_name": None,
            "client_url": None,
            "project_name": None,
            "brief_requirement": None,
            "detailed_requirement": None,
            "currency": "INR",
            "project_scale": "Medium",
            "last_active": time.time(),
        }
        return user_sessions[chat_id]


def clear_session(chat_id):
    """Remove a user session."""
    with sessions_lock:
        user_sessions.pop(chat_id, None)


# ─────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ brand.name }} — Proposal Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        beige: '#f0efe7',
                        charcoal: '#5a5a4a',
                        orange: '#ff8c42',
                        teal: '#50c8a3',
                        grid: '#e6e4d9',
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        display: ['Space Grotesk', 'sans-serif'],
                    },
                    borderRadius: {
                        lg: '0.75rem',
                        md: 'calc(0.75rem - 2px)',
                        sm: 'calc(0.75rem - 4px)',
                    }
                }
            }
        }
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        .card-hover { transition: all 0.3s ease; }
        .card-hover:hover { transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.08); border-color: #ff8c42; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .animate-in { animation: fadeInUp 0.5s ease forwards; opacity: 0; }
    </style>
</head>
<body class="bg-beige min-h-screen text-charcoal font-sans">
    <div class="max-w-5xl mx-auto px-6 py-12">
        <header class="flex items-center justify-between mb-12 animate-in">
            <div class="flex items-center gap-4">
                <img src="/static/LogoFull.png" alt="{{ brand.name }}" class="h-10 w-auto"> 
            </div>
            <!-- <div class="hidden sm:block text-sm font-medium text-charcoal/60">{{ brand.tagline }}</div> -->
             <a href="#" class="bg-orange text-white px-5 py-2 rounded-full font-medium hover:opacity-90 transition shadow-sm text-sm">
                <i class="fas fa-plus mr-2"></i>New Proposal
            </a>
        </header>

        <div class="text-center mb-16 animate-in" style="animation-delay: 0.1s">
            <h1 class="text-4xl md:text-5xl font-display font-bold text-charcoal mb-4">Proposal Dashboard</h1>
            <p class="text-charcoal/70 text-lg max-w-xl mx-auto">Manage and track all your generated proposals in one place.</p>
        </div>

        {% if proposals %}
        <div class="grid gap-4">
            {% for p in proposals %}
            <a href="{{ p.url }}" class="bg-white rounded-lg border border-grid p-6 card-hover block animate-in scheme-light" style="animation-delay: {{ loop.index * 0.05 + 0.2 }}s">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-5">
                        <div class="w-14 h-14 rounded-full bg-teal/20 text-teal flex items-center justify-center font-display font-bold text-xl shrink-0 border border-teal/20">
                            {{ p.client_name[0] | upper if p.client_name else '?' }}
                        </div>
                        <div>
                            <h3 class="font-display font-bold text-lg text-charcoal">{{ p.client_name }}</h3>
                            <p class="text-charcoal/60 text-sm font-medium">{{ p.project_name }}</p>
                        </div>
                    </div>
                    <div class="text-right hidden sm:block">
                        <p class="text-charcoal/50 text-xs font-mono mb-1">{{ p.created_at[:10] if p.created_at else '' }}</p>
                        <div class="inline-flex items-center gap-1 text-orange font-medium text-sm group">
                            <span>View Proposal</span>
                            <i class="fas fa-arrow-right text-xs transition-transform group-hover:translate-x-1"></i>
                        </div>
                    </div>
                </div>
            </a>
            {% endfor %}
        </div>
        {% else %}
        <div class="bg-white rounded-lg border border-grid p-16 text-center animate-in shadow-sm" style="animation-delay: 0.2s">
            <div class="w-20 h-20 bg-beige rounded-full flex items-center justify-center mx-auto mb-6">
                <i class="fas fa-inbox text-charcoal/40 text-3xl"></i>
            </div>
            <h3 class="font-display font-bold text-xl text-charcoal mb-2">No proposals yet</h3>
            <p class="text-charcoal/60 mb-8 max-w-md mx-auto">Start by sending <code class="bg-beige px-2 py-1 rounded text-orange font-mono">/pitch</code> to the Telegram bot.</p>
            
            <div class="bg-beige/50 rounded-lg p-5 max-w-sm mx-auto text-left border border-grid">
                <div class="flex items-center gap-3 mb-2">
                    <div class="w-8 h-8 rounded-full bg-teal text-white flex items-center justify-center shrink-0"><i class="fab fa-telegram-plane"></i></div>
                    <p class="text-charcoal font-medium text-sm">Quick Start</p>
                </div>
                <div class="pl-11">
                    <code class="text-orange font-bold text-sm block mb-1">/pitch</code>
                    <p class="text-charcoal/50 text-xs">The bot will guide you through the process step by step.</p>
                </div>
            </div>
        </div>
        {% endif %}

        <footer class="text-center mt-20 text-charcoal/40 text-sm font-medium">
            <p>&copy; 2026 {{ brand.name }}. All rights reserved.</p>
        </footer>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    proposals = load_proposals_index()
    return render_template_string(DASHBOARD_TEMPLATE, proposals=proposals, brand=MY_BRAND), 200, {
        "Cache-Control": "no-cache"
    }


@app.route("/proposal")
def latest_proposal():
    """Redirect to the latest proposal or show dashboard."""
    proposals = load_proposals_index()
    if proposals:
        return index()  # Show dashboard with all proposals
    proposal_path = os.path.join("static", "proposal.html")
    if os.path.exists(proposal_path):
        return send_file(proposal_path), 200, {"Cache-Control": "no-cache"}
    return index()


@app.route("/proposal/<proposal_id>")
def view_proposal(proposal_id):
    """Serve a specific proposal by its unique ID."""
    proposal_path = os.path.join("static", "proposals", proposal_id, "proposal.html")
    if os.path.exists(proposal_path):
        return send_file(proposal_path), 200, {"Cache-Control": "no-cache"}
    abort(404)


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename), 200, {"Cache-Control": "no-cache"}


# ─────────────────────────────────────────────
# Telegram Bot Handlers
# ─────────────────────────────────────────────

def get_proposal_base_url():
    """Get the base URL for proposal links."""
    if DOMAIN:
        return f"http://{DOMAIN}:8080"
    return "http://localhost:8080"


def escape_md2(text):
    """Escape text for MarkdownV2."""
    special = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special)}])', r'\\\1', str(text))


if bot:

    @bot.message_handler(commands=["start", "help"])
    def handle_start(message):
        bot.reply_to(
            message,
            "🚀 *Welcome to Sparktoship Proposal Generator\\!*\n\n"
            "Available commands:\n\n"
            "📝 `/pitch` — Start creating a new proposal \\(guided\\)\n"
            "📋 `/proposals` — View all generated proposals\n"
            "❌ `/cancel` — Cancel current pitch session\n\n"
            "_You can also use the quick format:_\n"
            "`/pitch https://example\\.com Project Name`",
            parse_mode="MarkdownV2",
        )

    @bot.message_handler(commands=["cancel"])
    def handle_cancel(message):
        session = get_session(message.chat.id)
        if session:
            clear_session(message.chat.id)
            bot.reply_to(message, "❌ Pitch session cancelled. Send /pitch to start a new one.")
        else:
            bot.reply_to(message, "No active pitch session to cancel.")

    @bot.message_handler(commands=["proposals"])
    def handle_proposals(message):
        proposals = load_proposals_index()
        if not proposals:
            bot.reply_to(message, "📋 No proposals generated yet. Send /pitch to create one!")
            return

        base_url = get_proposal_base_url()
        lines = ["📋 *Recent Proposals:*\n"]
        for i, p in enumerate(proposals[:10], 1):
            date_str = p.get("created_at", "")[:10]
            url = f"{base_url}{p['url']}"
            lines.append(
                f"{i}\\. *{escape_md2(p['client_name'])}* — {escape_md2(p['project_name'])}\n"
                f"   📅 {escape_md2(date_str)} • 🔗 [View Proposal]({escape_md2(url)})"
            )

        bot.reply_to(message, "\n\n".join(lines), parse_mode="MarkdownV2",
                     disable_web_page_preview=True)

    @bot.message_handler(commands=["pitch"])
    def handle_pitch(message):
        parts = message.text.split(maxsplit=2)

        # Quick format: /pitch <url> [project_name]  (backward compatible)
        if len(parts) >= 2 and parts[1].startswith(("http://", "https://", "www.")):
            client_url = parts[1]
            project_name = parts[2] if len(parts) > 2 else None

            if not client_url.startswith(("http://", "https://")):
                client_url = "https://" + client_url

            bot.reply_to(message, f"⏳ Analyzing {client_url} for proposal... Please wait.")

            try:
                result = build_proposal(
                    client_url=client_url,
                    project_name=project_name,
                    app=app
                )
                _send_proposal_result(message, result)
            except Exception as e:
                bot.reply_to(message, f"❌ Error generating proposal: {str(e)}")
            return

        # Guided flow: just /pitch
        create_session(message.chat.id)
        bot.reply_to(
            message,
            "📝 *Let's create a proposal\\!*\n\n"
            "What's the *client name*?\n"
            "Also share their *website URL* if they have one\\.\n\n"
            "_Example:_ `Acme Corp https://acme\\.com`\n"
            "_No website:_ `Acme Corp skip`",
            parse_mode="MarkdownV2",
        )

    # ─────────────────────────────────────────
    # Document upload handler
    # ─────────────────────────────────────────

    @bot.message_handler(content_types=["document"])
    def handle_document_upload(message):
        session = get_session(message.chat.id)
        if not session or session["step"] != STEP_AWAITING_DOCUMENT:
            bot.reply_to(
                message,
                "📎 To upload a requirements document, first start a pitch session with /pitch"
            )
            return

        doc = message.document
        filename = doc.file_name or "unknown.txt"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in (".txt", ".md", ".markdown", ".pdf"):
            bot.reply_to(
                message,
                f"⚠️ Unsupported file type: `{ext}`\n"
                "Please upload a *.txt*, *.md*, or *.pdf* file.\n"
                "Or type *skip* to proceed without a detailed document.",
                parse_mode="Markdown"
            )
            return

        # Check file size
        if doc.file_size and doc.file_size > 5 * 1024 * 1024:
            bot.reply_to(message, "⚠️ File too large. Maximum size is 5MB.\nType *skip* to proceed without it.",
                         parse_mode="Markdown")
            return

        bot.reply_to(message, f"📄 Processing `{filename}`...", parse_mode="Markdown")

        try:
            file_info = bot.get_file(doc.file_id)
            downloaded = bot.download_file(file_info.file_path)

            text, error = parse_uploaded_file(downloaded, filename)
            if error:
                bot.reply_to(message, f"⚠️ {error}\nType *skip* to proceed without the document.",
                             parse_mode="Markdown")
                return

            session["detailed_requirement"] = text
            word_count = len(text.split())
            bot.reply_to(
                message,
                f"✅ Extracted *{word_count} words* from `{filename}`\n\n"
                f"⏳ Generating your proposal now... Please wait\\.",
                parse_mode="MarkdownV2"
            )

            _generate_and_send(message, session)

        except Exception as e:
            bot.reply_to(message, f"❌ Error processing file: {str(e)}\nType *skip* to proceed without it.",
                         parse_mode="Markdown")

    # ─────────────────────────────────────────
    # General text handler (conversational flow)
    # ─────────────────────────────────────────

    @bot.message_handler(func=lambda msg: True, content_types=["text"])
    def handle_text(message):
        session = get_session(message.chat.id)
        if not session:
            return  # Not in a session, ignore non-command messages

        text = message.text.strip()

        # Allow cancel at any step
        if text.lower() in ("/cancel", "cancel"):
            clear_session(message.chat.id)
            bot.reply_to(message, "❌ Pitch session cancelled.")
            return

        # ── Step 1: Client name & website ──
        if session["step"] == STEP_AWAITING_CLIENT_INFO:
            _handle_client_info(message, session, text)

        # ── Step 2: Brief requirement ──
        elif session["step"] == STEP_AWAITING_BRIEF:
            _handle_brief(message, session, text)

        # ── Step 3: Currency preference ──
        elif session["step"] == STEP_AWAITING_CURRENCY:
            _handle_currency(message, session, text)

        # ── Step 4: Project Scale ──
        elif session["step"] == STEP_AWAITING_SCALE:
            _handle_scale(message, session, text)

        # ── Step 5: Detailed document ──
        elif session["step"] == STEP_AWAITING_DOCUMENT:
            _handle_document_step(message, session, text)

    # ─────────────────────────────────────────
    # Step handlers
    # ─────────────────────────────────────────

    def _handle_client_info(message, session, text):
        """Parse client name and optional URL from user message."""
        # Try to find a URL in the message
        url_pattern = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
        url_match = url_pattern.search(text)

        if url_match:
            client_url = url_match.group(1)
            if not client_url.startswith(("http://", "https://")):
                client_url = "https://" + client_url
            # Everything before the URL is the client name
            client_name = text[:url_match.start()].strip()
            # If name is after URL, check after
            if not client_name:
                client_name = text[url_match.end():].strip()
            session["client_url"] = client_url
        else:
            # No URL — check for "skip"
            client_name = text.replace("skip", "").strip()
            session["client_url"] = None

        if not client_name:
            bot.reply_to(
                message,
                "⚠️ Please provide at least the *client name*\\.\n\n"
                "_Example:_ `Acme Corp https://acme\\.com`\n"
                "_No website:_ `Acme Corp skip`",
                parse_mode="MarkdownV2",
            )
            return

        session["client_name"] = client_name
        session["step"] = STEP_AWAITING_BRIEF

        url_ack = f" ({session['client_url']})" if session["client_url"] else " (no website)"
        bot.reply_to(
            message,
            f"✅ Client: *{escape_md2(client_name)}*{escape_md2(url_ack)}\n\n"
            f"Now describe the *project requirement* in brief \\(100 words or less\\)\\.\n\n"
            f"_Example: Need a cloud migration for legacy ERP to AWS with CI/CD pipeline\\._",
            parse_mode="MarkdownV2",
        )

    def _handle_brief(message, session, text):
        """Capture brief requirement."""
        if text.lower() == "skip":
            session["brief_requirement"] = None
        else:
            session["brief_requirement"] = text[:500]  # Cap at ~500 chars

        session["step"] = STEP_AWAITING_CURRENCY

        bot.reply_to(
            message,
            "✅ Got it\\!\n\n"
            "What *currency* should the proposal use for pricing?\n\n"
            "💰 Type `INR` for Indian Rupees \\(₹\\)\n"
            "💵 Type `USD` for US Dollars \\(\\$\\)",
            parse_mode="MarkdownV2",
        )

    def _handle_currency(message, session, text):
        """Capture currency preference."""
        choice = text.strip().upper()
        if choice in ("INR", "₹", "RUPEES", "RUPEE"):
            session["currency"] = "INR"
        elif choice in ("USD", "$", "DOLLAR", "DOLLARS"):
            session["currency"] = "USD"
        else:
            bot.reply_to(
                message,
                "⚠️ Please type *INR* or *USD*",
                parse_mode="Markdown",
            )
            return

        currency_label = "₹ INR" if session["currency"] == "INR" else "$ USD"
        session["step"] = STEP_AWAITING_SCALE

        bot.reply_to(
            message,
            f"✅ Currency: *{escape_md2(currency_label)}*\n\n"
            "What is the estimated *scale* of this project?\n\n"
            "🌱 `Small` \\(MVP, simple site/app\\)\n"
            "🚀 `Medium` \\(Standard full\\-stack solution\\)\n"
            "🏢 `High` \\(Enterprise, complex architecture\\)",
            parse_mode="MarkdownV2",
        )

    def _handle_scale(message, session, text):
        """Capture project scale."""
        choice = text.strip().lower()
        if "small" in choice:
            session["project_scale"] = "Small"
        elif "high" in choice or "large" in choice or "enterprise" in choice:
            session["project_scale"] = "High"
        else:
            session["project_scale"] = "Medium"

        scale_label = session["project_scale"]
        session["step"] = STEP_AWAITING_DOCUMENT

        bot.reply_to(
            message,
            f"✅ Scale: *{scale_label}*\n\n"
            "Do you have a *detailed requirement document*?\n\n"
            "📄 *Upload a file* \\(\\.txt, \\.md, \\.pdf\\)\n"
            "🔗 *Share a link* \\(Google Drive, Dropbox, etc\\.\\)\n"
            "⏭ Type `skip` to proceed with just the brief\n\n"
            "_This helps generate a more accurate proposal\\._",
            parse_mode="MarkdownV2",
        )

    def _handle_document_step(message, session, text):
        """Handle text input during document step — either a URL or skip."""
        if text.lower() == "skip":
            bot.reply_to(message, "⏳ Generating your proposal... Please wait.")
            _generate_and_send(message, session)
            return

        # Check if it's a URL
        url_pattern = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
        url_match = url_pattern.search(text)

        if url_match:
            doc_url = url_match.group(1)
            if not doc_url.startswith(("http://", "https://")):
                doc_url = "https://" + doc_url

            bot.reply_to(message, f"🔗 Fetching document from URL...")

            doc_text, error = fetch_remote_document(doc_url)
            if error:
                bot.reply_to(
                    message,
                    f"⚠️ {error}\n\n"
                    "You can try another link, upload a file, or type *skip* to proceed.",
                    parse_mode="Markdown"
                )
                return

            session["detailed_requirement"] = doc_text
            word_count = len(doc_text.split())
            bot.reply_to(message, f"✅ Extracted *{word_count} words* from the document.\n\n"
                                  f"⏳ Generating your proposal now... Please wait.",
                         parse_mode="Markdown")
            _generate_and_send(message, session)
        else:
            bot.reply_to(
                message,
                "⚠️ That doesn't look like a URL\\.\n\n"
                "📄 *Upload a file* \\(\\.txt, \\.md, \\.pdf\\)\n"
                "🔗 *Share a public link* to the document\n"
                "⏭ Type `skip` to proceed without it",
                parse_mode="MarkdownV2",
            )

    # ─────────────────────────────────────────
    # Proposal generation & delivery
    # ─────────────────────────────────────────

    def _generate_and_send(message, session):
        """Generate the proposal and send the result."""
        try:
            result = build_proposal(
                client_name=session.get("client_name"),
                client_url=session.get("client_url"),
                project_name=session.get("project_name"),
                brief_requirement=session.get("brief_requirement"),
                detailed_requirement=session.get("detailed_requirement"),
                currency=session.get("currency", "INR"),
                project_scale=session.get("project_scale", "Medium"),
                app=app
            )
            _send_proposal_result(message, result)
        except Exception as e:
            bot.reply_to(message, f"❌ Error generating proposal: {str(e)}")
        finally:
            clear_session(message.chat.id)

    def _send_proposal_result(message, result):
        """Send the generated proposal to the user."""
        base_url = get_proposal_base_url()
        proposal_url = f"{base_url}{result.get('proposal_url', '/proposal')}"

        caption = (
            f"✅ Proposal ready for **{result['client']['name']}**!\n\n"
            f"📌 Project: **{result['project_name']}**\n"
            f"🔗 View: {proposal_url}"
        )

        # Try to send with architecture diagram
        proposal_id = result.get("proposal_id", "")
        diagram_path = os.path.join("static", "proposals", proposal_id, "architecture.png")

        if os.path.exists(diagram_path):
            try:
                with open(diagram_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="Markdown")
                return
            except Exception as e:
                print(f"[Bot] Error sending photo: {e}")

        bot.reply_to(message, caption, parse_mode="Markdown")

    # ─────────────────────────────────────────
    # Bot polling
    # ─────────────────────────────────────────

    def run_bot():
        print("[Bot] Starting Telegram bot polling...")
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"[Bot] Polling error: {e}")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("[Bot] Telegram bot thread started.")
else:
    print("[Bot] No TELEGRAM_BOT_TOKEN set. Bot disabled. Set it in Secrets.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
