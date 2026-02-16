# Sparktoship Co-Branded Proposal Generator

## Overview
A Python application integrating a Telegram Bot with a co-branded proposal generator. When a client URL is sent to the bot via `/pitch`, it scrapes the client's branding (logo, colors), generates an architecture diagram using Mermaid, and creates a professional co-branded HTML proposal page.

## Project Architecture
- **main.py** — Flask web server (port 5000) + Telegram bot (polling in background thread)
- **generator.py** — Client website scraper, Mermaid diagram generator, HTML proposal compiler
- **templates/proposal.html** — Jinja2 template with Tailwind CSS for the co-branded proposal
- **static/** — Generated assets (architecture.png, proposal.html output)

## Tech Stack
- Python 3.11 (Flask, pyTelegramBotAPI, Requests, BeautifulSoup)
- Node.js 20 (for @mermaid-js/mermaid-cli diagram generation)
- Tailwind CSS (via CDN), Font Awesome icons

## Key Features
- `/pitch <url> [project_name]` Telegram command triggers proposal generation
- Scrapes client logo (favicons, og:image, meta tags) and primary color (theme-color)
- Generates Mermaid architecture diagram (Client App -> API Gateway -> Microservices -> DB)
- Renders co-branded HTML with dual-logo header, hero section, architecture diagram, tech stack details
- Flask serves proposal at `/proposal` and static assets

## Required Secrets
- `TELEGRAM_BOT_TOKEN` — Token from @BotFather on Telegram

## Recent Changes
- 2026-02-16: Initial build — all core files created
