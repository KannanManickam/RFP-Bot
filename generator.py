import os
import re
import subprocess
import ipaddress
import socket
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from flask import render_template
from openai import OpenAI

# Initialize OpenAI client with Replit AI Integrations
# This internally uses Replit AI Integrations for OpenAI access, 
# does not require your own API key, and charges are billed to your credits.
client_ai = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

def get_ai_content(client_name, project_name):
    """Generate dynamic content for the proposal using gpt-5."""
    # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
    # do not change this unless explicitly requested by the user
    prompt = f"""
    Create a technical proposal snippet for a project named '{project_name}' for the client '{client_name}'.
    Return a JSON object with:
    1. 'hero_desc': A 1-2 sentence compelling description.
    2. 'features': Array of 3 objects with 'title', 'icon' (FontAwesome class like 'fas fa-shield'), and 'desc'.
    3. 'tech_stack': Object with 'backend' (array of 4 strings) and 'data' (array of 4 strings).
    
    Keep it professional and specific to solution architecture.
    """
    try:
        response = client_ai.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def is_safe_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr in resolved:
            ip = ipaddress.ip_address(addr[0])
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True

MY_BRAND = {
    "name": "Sparktoship",
    "website": "https://sparktoship.com",
    "tagline": "Solution Architecture & Engineering",
}


def scrape_client(client_url):
    client_data = {
        "name": urlparse(client_url).netloc.replace("www.", "").split(".")[0].capitalize(),
        "url": client_url,
        "logo": None,
        "color": "#3B82F6",
    }

    if not is_safe_url(client_url):
        print(f"[Scraper] Blocked unsafe URL: {client_url}")
        return client_data

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(client_url, headers=headers, timeout=10, allow_redirects=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            raw = title_tag.string.strip().split("|")[0].split("-")[0].split("–")[0].strip()
            if raw:
                client_data["name"] = raw[:40]

        logo = None
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            logo = urljoin(client_url, og_image["content"])

        if not logo:
            for rel in [["icon"], ["shortcut", "icon"], ["apple-touch-icon"]]:
                link = soup.find("link", rel=rel)
                if link and link.get("href"):
                    logo = urljoin(client_url, link["href"])
                    break

        if not logo:
            favicon_url = urljoin(client_url, "/favicon.ico")
            try:
                r = requests.head(favicon_url, timeout=5)
                if r.status_code == 200:
                    logo = favicon_url
            except Exception:
                pass

        if logo:
            client_data["logo"] = logo

        color = None
        theme_color = soup.find("meta", attrs={"name": "theme-color"})
        if theme_color and theme_color.get("content"):
            color = theme_color["content"]

        if not color:
            ms_color = soup.find("meta", attrs={"name": "msapplication-TileColor"})
            if ms_color and ms_color.get("content"):
                color = ms_color["content"]

        if not color:
            style_tags = soup.find_all("style")
            for st in style_tags:
                if st.string:
                    hex_match = re.search(r"#(?:[0-9a-fA-F]{6})", st.string)
                    if hex_match:
                        color = hex_match.group(0)
                        break

        if color and re.match(r"^#(?:[0-9a-fA-F]{3,8})$", color):
            client_data["color"] = color

    except Exception as e:
        print(f"[Scraper] Error scraping {client_url}: {e}")

    return client_data


def generate_diagram(client_name):
    os.makedirs("static", exist_ok=True)

    mermaid_code = f"""graph LR
    A["{client_name} App"] -->|REST API| B["Sparktoship\\nAPI Gateway"]
    B -->|Route| C["Auth\\nService"]
    B -->|Route| D["Core\\nMicroservice"]
    B -->|Route| E["Analytics\\nService"]
    C -->|JWT| F[("User DB")]
    D -->|CRUD| G[("Primary DB")]
    E -->|Write| H[("Analytics DB")]
    D -->|Events| I["Message Queue"]
    I -->|Subscribe| E

    style A fill:#4F46E5,stroke:#3730A3,color:#fff
    style B fill:#0EA5E9,stroke:#0284C7,color:#fff
    style C fill:#10B981,stroke:#059669,color:#fff
    style D fill:#10B981,stroke:#059669,color:#fff
    style E fill:#10B981,stroke:#059669,color:#fff
    style F fill:#F59E0B,stroke:#D97706,color:#fff
    style G fill:#F59E0B,stroke:#D97706,color:#fff
    style H fill:#F59E0B,stroke:#D97706,color:#fff
    style I fill:#8B5CF6,stroke:#7C3AED,color:#fff
"""

    mmd_path = os.path.join("static", "temp.mmd")
    out_path = os.path.join("static", "architecture.png")

    with open(mmd_path, "w") as f:
        f.write(mermaid_code)

    try:
        # Mermaid CLI on Replit/Nix can be finicky with arguments. 
        # Using a simpler call and ensuring paths are absolute or handled correctly.
        mmd_abs = os.path.abspath(mmd_path)
        out_abs = os.path.abspath(out_path)
        
        # Simplified command to avoid "too many arguments" errors seen in logs
        cmd = [
            "npx", "-y", "@mermaid-js/mermaid-cli", "mmdc",
            "-i", mmd_abs,
            "-o", out_abs,
            "-b", "transparent"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[Mermaid] stderr: {result.stderr}")
            return False
        return os.path.exists(out_path)
    except Exception as e:
        print(f"[Mermaid] Error: {e}")
        return False


def build_proposal(client_url, project_name, app=None):
    client_data = scrape_client(client_url)
    if project_name:
        client_data["project_name"] = project_name
    else:
        client_data["project_name"] = f"{client_data['name']} Integration"

    # Fetch AI-generated dynamic content
    ai_content = get_ai_content(client_data["name"], client_data["project_name"])

    diagram_ok = generate_diagram(client_data["name"])

    template_data = {
        "client": client_data,
        "my_brand": MY_BRAND,
        "diagram_available": diagram_ok,
        "project_name": client_data["project_name"],
        "ai": ai_content
    }

    if app:
        with app.app_context():
            html = render_template("proposal.html", **template_data)
    else:
        html = render_template("proposal.html", **template_data)

    output_path = os.path.join("static", "proposal.html")
    with open(output_path, "w") as f:
        f.write(html)

    return template_data
