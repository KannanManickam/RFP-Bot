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
client_ai = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

MY_BRAND = {
    "name": "Sparktoship",
    "website": "https://sparktoship.com",
    "tagline": "Solution Architecture & Engineering",
}

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

def get_ai_content(client_name, project_name, client_url):
    """Generate dynamic content for the proposal using gpt-5."""
    # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
    prompt = f"""
    Create a comprehensive technical proposal for a project named '{project_name}' for the client '{client_name}' ({client_url}).
    IMPORTANT: Use Indian market competitive pricing (INR based, then convert to USD). 
    A typical small-mid scale project in India might range from ₹2,00,000 to ₹10,00,000.
    
    Return a JSON object with:
    1. 'hero_desc': A 1-2 sentence compelling description.
    2. 'executive_summary': A professional overview of the project goals.
    3. 'scope_of_work': Array of 4-5 key deliverables.
    4. 'roadmap': Array of 3-4 phases with 'phase' and 'details'.
    5. 'pricing': Object with:
        - 'usd': String (e.g. '$5,000')
        - 'inr': String (e.g. '₹4,15,000')
        - 'terms': String (e.g. '30% Advance, 40% Mid-way, 30% Deployment')
        - 'breakdown': Array of objects with 'item' and 'cost' (show both USD and INR)
    6. 'resources': Array of objects with 'role' and 'allocation' (e.g. 'Part-time', 'Milestone-based').
    7. 'key_notes': Array of 3 important considerations.
    8. 'tech_stack': Object with 'backend' (array) and 'data' (array).
    9. 'mermaid_diagram': A simple, valid Mermaid.js 'graph TD' string. 
       USE ONLY SIMPLE TEXT IN QUOTES.
       Example: 'graph TD\nA["User"] --> B["API"]\nB --> C["DB"]'
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

def scrape_client(client_url):
    client_data = {
        "name": urlparse(client_url).netloc.replace("www.", "").split(".")[0].capitalize(),
        "url": client_url,
        "logo": None,
        "color": "#3B82F6",
    }
    if not is_safe_url(client_url):
        return client_data
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(client_url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            raw = title_tag.string.strip().split("|")[0].split("-")[0].strip()
            if raw: client_data["name"] = raw[:40]
        
        logo = None
        og_image = soup.find("meta", property="og:image")
        if og_image: logo = urljoin(client_url, og_image.get("content"))
        if not logo:
            link = soup.find("link", rel=re.compile("icon", re.I))
            if link: logo = urljoin(client_url, link.get("href"))
        if logo: client_data["logo"] = logo

        theme_color = soup.find("meta", attrs={"name": "theme-color"})
        if theme_color: client_data["color"] = theme_color.get("content")
    except Exception as e:
        print(f"Scrape error: {e}")
    return client_data

def generate_diagram(mermaid_code):
    """Generate diagram using mermaid-cli with explicit fallback to client-side rendering."""
    if not mermaid_code: 
        print("[Mermaid] No code provided")
        return False
    
    os.makedirs("static", exist_ok=True)
    mmd_path = os.path.abspath("static/temp.mmd")
    out_path = os.path.abspath("static/architecture.png")
    
    # Ensure graph TD is present
    cleaned_code = mermaid_code.strip()
    if not any(cleaned_code.startswith(t) for t in ["graph", "flowchart", "sequenceDiagram"]):
        cleaned_code = "graph TD\n" + cleaned_code

    with open(mmd_path, "w") as f: 
        f.write(cleaned_code)
        
    print(f"[Mermaid] Generating diagram from code:\n{cleaned_code}")
    
    try:
        # The 'too many arguments' error usually comes from how npx or the shell handles arguments.
        # We'll use a more direct approach or check if mermaid-cli is in node_modules
        cli_path = "./node_modules/.bin/mmdc"
        if os.path.exists(cli_path):
            cmd = [cli_path, "-i", mmd_path, "-o", out_path, "-b", "transparent", "-p", "puppeteer_config.json"]
        else:
            cmd = ["npx", "-y", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", mmd_path, "-o", out_path, "-b", "transparent"]
        
        # Create a basic puppeteer config to help with sandbox issues in Nix
        with open("puppeteer_config.json", "w") as f:
            json.dump({"args": ["--no-sandbox", "--disable-setuid-sandbox"]}, f)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(out_path):
            print("[Mermaid] Successfully generated diagram image.")
            return True
        else:
            print(f"[Mermaid] CLI Failed. Return code: {result.returncode}")
            print(f"[Mermaid] Stdout: {result.stdout}")
            print(f"[Mermaid] Stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"[Mermaid] Exception during generation: {e}")
        return False

def build_proposal(client_url, project_name, app=None):
    client_data = scrape_client(client_url)
    p_name = project_name if project_name else f"{client_data['name']} Digital Transformation"
    ai_content = get_ai_content(client_data["name"], p_name, client_url)
    
    # Try generating image
    diagram_ok = generate_diagram(ai_content.get("mermaid_diagram") if ai_content else None)
    
    template_data = {
        "client": client_data,
        "my_brand": MY_BRAND,
        "diagram_available": diagram_ok,
        "mermaid_code": ai_content.get("mermaid_diagram") if ai_content else None,
        "project_name": p_name,
        "ai": ai_content
    }
    
    if app:
        with app.app_context():
            html = render_template("proposal.html", **template_data)
    else:
        html = render_template("proposal.html", **template_data)
        
    with open("static/proposal.html", "w") as f: f.write(html)
    return template_data
