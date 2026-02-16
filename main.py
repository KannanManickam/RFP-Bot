import os
import threading
import telebot
from flask import Flask, send_from_directory, send_file

from generator import build_proposal

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", "")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False) if TELEGRAM_TOKEN else None


@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sparktoship Proposal Generator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    </head>
    <body class="bg-slate-900 min-h-screen flex items-center justify-center">
        <div class="text-center text-white">
            <i class="fas fa-rocket text-sky-400 text-6xl mb-6"></i>
            <h1 class="text-4xl font-bold mb-2">Sparktoship</h1>
            <p class="text-gray-400 text-lg mb-8">Co-Branded Proposal Generator</p>
            <div class="bg-slate-800 rounded-xl p-6 max-w-md mx-auto text-left">
                <p class="text-gray-300 mb-3">Send this command to the Telegram bot:</p>
                <code class="bg-slate-700 text-sky-400 px-4 py-2 rounded block text-sm">
                    /pitch https://example.com Project Name
                </code>
                <p class="text-gray-500 text-sm mt-3">The bot will generate a co-branded proposal page.</p>
            </div>
            <div class="mt-6">
                <a href="/proposal" class="text-sky-400 hover:underline text-sm">
                    <i class="fas fa-file-lines mr-1"></i> View Latest Proposal
                </a>
            </div>
        </div>
    </body>
    </html>
    """, 200, {"Cache-Control": "no-cache"}


@app.route("/proposal")
def proposal():
    proposal_path = os.path.join("static", "proposal.html")
    if os.path.exists(proposal_path):
        return send_file(proposal_path), 200, {"Cache-Control": "no-cache"}
    return "<h1>No proposal generated yet.</h1><p>Use /pitch command in Telegram bot.</p>", 404


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename), 200, {"Cache-Control": "no-cache"}


if bot:
    @bot.message_handler(commands=["start", "help"])
    def handle_start(message):
        bot.reply_to(
            message,
            "Welcome to *Sparktoship Proposal Generator*\\!\n\n"
            "Use the command:\n"
            "`/pitch <url> <project_name>`\n\n"
            "Example:\n"
            "`/pitch https://example\\.com Cloud Migration`",
            parse_mode="MarkdownV2",
        )

    @bot.message_handler(commands=["pitch"])
    def handle_pitch(message):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /pitch <url> [project_name]\n\nExample: /pitch https://example.com My Project")
            return

        client_url = parts[1]
        project_name = parts[2] if len(parts) > 2 else None

        if not client_url.startswith(("http://", "https://")):
            client_url = "https://" + client_url

        bot.reply_to(message, f"Analyzing {client_url} for Sparktoship proposal... Please wait.")

        try:
            result = build_proposal(client_url, project_name, app=app)

            if DOMAIN:
                proposal_url = f"https://{DOMAIN}/proposal"
            else:
                proposal_url = "http://localhost:5000/proposal"

            caption = (
                f"Proposal ready for **{result['client']['name']}**!\n\n"
                f"Project: **{result['project_name']}**\n"
                f"View: {proposal_url}"
            )

            diagram_path = os.path.join("static", "architecture.png")
            if os.path.exists(diagram_path):
                with open(diagram_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="Markdown")
            else:
                bot.reply_to(message, caption, parse_mode="Markdown")

        except Exception as e:
            bot.reply_to(message, f"Error generating proposal: {str(e)}")

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
    app.run(host="0.0.0.0", port=5000, debug=False)
