# ─── Stage 1: Node dependencies (for Mermaid CLI) ───
FROM node:20-slim AS node-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production

# ─── Stage 2: Final image ───
FROM python:3.12-slim

# Install system dependencies for Puppeteer/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Set Puppeteer to use system Chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# Install Node.js runtime (needed for mmdc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Node modules from stage 1
COPY --from=node-deps /app/node_modules ./node_modules
COPY package.json package-lock.json ./

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    beautifulsoup4 \
    flask \
    gunicorn \
    openai \
    pdfplumber \
    python-dotenv \
    pytelegrambotapi \
    requests

# Copy application code
COPY main.py generator.py document_parser.py image_generator.py puppeteer_config.json ./
COPY templates/ templates/
COPY static/ static/
COPY public/ static/

# Create static directories
RUN mkdir -p static/proposals static/generated

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# Run with gunicorn for production
CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "main:app"]
