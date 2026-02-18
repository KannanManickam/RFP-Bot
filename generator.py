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
    Return a JSON object with:
    1. 'hero_desc': A 1-2 sentence compelling description.
    2. 'executive_summary': A professional overview of the project goals.
    3. 'scope_of_work': Array of 4-5 key deliverables.
    4. 'roadmap': Array of 3-4 phases with 'phase' and 'details'.
    5. 'pricing': Object with 'amount' (e.g. '$15,000 - $25,000'), 'terms' (e.g. '50% upfront'), and 'notes'.
    6. 'key_notes': Array of 3 important considerations or assumptions.
    7. 'tech_stack': Object with 'backend' (array of 4 strings) and 'data' (array of 4 strings).
    8. 'mermaid_diagram': A Mermaid.js 'graph LR' string representing the SPECIFIC architecture for this client/project. 
       Use 'A["Client"] --> B["Service"]' format. Keep it clean and professional. Use line breaks carefully.
    
    Ensure the content is specific to the client's likely needs based on their name and project.
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
        resp = requests.get(client_url, headers=headers, timeout=10, allow_redirects=False)
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
    if not mermaid_code: return False
    os.makedirs("static", exist_ok=True)
    mmd_path = os.path.abspath("static/temp.mmd")
    out_path = os.path.abspath("static/architecture.png")
    with open(mmd_path, "w") as f: f.write(mermaid_code)
    try:
        subprocess.run(["npx", "-y", "@mermaid-js/mermaid-cli", "mmdc", "-i", mmd_path, "-o", out_path, "-b", "transparent"], 
                       capture_output=True, timeout=60)
        return os.path.exists(out_path)
    except: return False

def build_proposal(client_url, project_name, app=None):
    client_data = scrape_client(client_url)
    p_name = project_name if project_name else f"{client_data['name']} Digital Transformation"
    ai_content = get_ai_content(client_data["name"], p_name, client_url)
    
    diagram_ok = generate_diagram(ai_content.get("mermaid_diagram") if ai_content else None)
    
    template_data = {
        "client": client_data,
        "my_brand": MY_BRAND,
        "diagram_available": diagram_ok,
        "project_name": p_name,
        "ai": ai_content
    }
    
    with (app.app_context() if app else ExitStack()):
        html = render_template("proposal.html", **template_data)
        
    with open("static/proposal.html", "w") as f: f.write(html)
    return template_data
