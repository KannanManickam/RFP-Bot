# 🚀 Deal-Closer Bot

> **Your AI-Powered Sales Proposal Generator**  
> _Turn client briefs into professional, comprehensive technical proposals in minutes._

![Project Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)
![Python Version](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

The **Deal-Closer Bot** is an intelligent automation tool designed to streamline the sales process for technical agencies and freelancers. By interacting with a Telegram bot, users can provide client details, project briefs, and even upload detailed requirement documents (PDF/TXT). The bot then leverages AI to generate a full-fledged HTML proposal complete with pricing, roadmap, team structure, and an architecture diagram.

---

## ✨ Features

- **🤖 Interactive Telegram Bot**: Guided conversation flow to collect project requirements effortlessly.
- **📄 AI-Generated Proposals**: Creates detailed, professional HTML proposals tailored to each client.
- **Iy Convert Briefs to Plans**: Takes simple text briefs or uploaded documents and expands them into full scopes of work.
- **🕸️ Client Intelligence**: Automatically scrapes client websites to extract branding, logos, and color schemes for personalized proposals.
- **📊 Automated Architecture Diagrams**: Generates system architecture diagrams using Mermaid.js and embeds them directly into the proposal.
- **🗄️ Centralized Web Dashboard**: A sleek, dark-mode dashboard to view, manage, and share all generated proposals.
- **💰 Smart Pricing**: Supports both **INR (₹)** and **USD ($)** with context-aware pricing models.
- **📂 Document Parsing**: Supports uploading requirement files (`.pdf`, `.txt`, `.md`) for deep analysis.

---

## 🛠️ Tech Stack

- **Backend**: Python (Flask)
- **Bot Interface**: [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- **AI Engine**: OpenAI API (GPT Models)
- **Frontend**: HTML5, TailwindCSS
- **Diagramming**: Mermaid.js & Puppeteer (for image generation)
- **Infrastructure**: Docker, Gunicorn

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js & npm (for Mermaid CLI)
- A Telegram Bot Token (via [@BotFather](https://t.me/botfather))
- OpenAI API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Deal-Closer-Bot
   ```

2. **Install Python Dependencies**
   This project uses `uv` for dependency management, but you can also use pip.
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r pyproject.toml
   ```

3. **Install Node.js Dependencies** (for diagram generation)
   ```bash
   npm install
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```bash
   cp .env.example .env  # if example exists, otherwise create new
   ```
   Add the following variables:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   AI_INTEGRATIONS_OPENAI_API_KEY=your_openai_api_key
   APP_DOMAIN=your-domain.com  # Optional: for production URL generation
   ```

### Running the Application

Start the Flask server and Bot poller:

```bash
python main.py
```

The server will start at `http://localhost:8080`.

---

## 💡 Usage

### 1. Start a Pitch via Telegram
Send `/start` to your bot, then use the `/pitch` command.

- **Guided Mode**:
  Type `/pitch` and follow the prompts.
  1. Enter Client Name & Website.
  2. Provide a brief (or skip).
  3. Choose Currency (INR/USD).
  4. Upload a requirement document (or skip).

- **Quick Mode**:
  Type `/pitch https://client-website.com Project Name`

### 2. View Proposal
Once processing is complete, the bot will send you:
- A link to the **Web View** of the proposal.
- An image of the **System Architecture**.

### 3. Dashboard
Visit the root URL (e.g., `http://localhost:8080/`) to see a dashboard of all generated proposals.

---

## 📂 Project Structure

```
Deal-Closer-Bot/
├── main.py                 # Application entry point (Flask + Bot)
├── generator.py            # Proposal generation logic & AI integration
├── document_parser.py      # File upload & URL parsing logic
├── templates/              # HTML templates
│   └── proposal.html       # The proposal template
├── static/                 # Static assets
│   └── proposals/          # Generated proposals storage
├── pyproject.toml          # Python dependencies
├── package.json            # Node.js dependencies
└── Dockerfile              # Container configuration
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
