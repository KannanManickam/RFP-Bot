import os
import re
import subprocess
import ipaddress
import socket
import requests
import json
from datetime import datetime, timezone, timedelta
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

PROPOSALS_DIR = os.path.join("static", "proposals")
PROPOSALS_INDEX = os.path.join(PROPOSALS_DIR, "index.json")


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:50].strip('-')


def generate_proposal_id(client_name):
    """Generate a unique proposal ID from client name + timestamp."""
    slug = slugify(client_name) if client_name else "proposal"
    timestamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d-%H%M")
    return f"{slug}-{timestamp}"


def load_proposals_index():
    """Load the proposals index JSON."""
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    if os.path.exists(PROPOSALS_INDEX):
        try:
            with open(PROPOSALS_INDEX, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_proposals_index(index):
    """Save the proposals index JSON."""
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    with open(PROPOSALS_INDEX, "w") as f:
        json.dump(index, f, indent=2, default=str)


def add_to_index(proposal_id, client_name, project_name, client_url=None):
    """Add a new proposal entry to the index."""
    index = load_proposals_index()
    entry = {
        "id": proposal_id,
        "client_name": client_name,
        "project_name": project_name,
        "client_url": client_url,
        "created_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(),
        "url": f"/proposal/{proposal_id}"
    }
    index.insert(0, entry)  # newest first
    save_proposals_index(index)
    return entry


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


def get_ai_content(client_name, project_name, client_url=None,
                   brief_requirement=None, detailed_requirement=None,
                   currency="INR"):
    """Generate dynamic content for the proposal using AI."""

    # Build context sections
    context_parts = []

    if client_url:
        context_parts.append(f"Client website: {client_url}")

    if brief_requirement:
        context_parts.append(f"Project brief (from client): {brief_requirement}")

    if detailed_requirement:
        context_parts.append(
            f"Detailed requirements document (from client):\n"
            f"---\n{detailed_requirement}\n---"
        )

    context_block = "\n\n".join(context_parts) if context_parts else "No additional context provided."

    # Currency-specific pricing guidance
    if currency == "INR":
        pricing_guidance = (
            "Use INR (Indian Rupees) ONLY for all pricing. Use the ₹ symbol. "
            "A typical small-mid scale project in India ranges from ₹2,00,000 to ₹10,00,000. "
            "Format amounts Indian style (e.g. ₹6,50,000)."
        )
    else:
        pricing_guidance = (
            "Use USD (US Dollars) ONLY for all pricing. Use the $ symbol. "
            "A typical small-mid scale project ranges from $3,000 to $15,000. "
            "Format amounts US style (e.g. $7,500)."
        )

    prompt = f"""
    Create a comprehensive technical proposal for a project named '{project_name}' for the client '{client_name}'.

    CONTEXT PROVIDED:
    {context_block}

    IMPORTANT GUIDELINES:
    - {pricing_guidance}
    - Use ONLY {currency} currency throughout. Do NOT show dual currencies.
    - If a brief or detailed requirement is provided, tailor the proposal SPECIFICALLY to those requirements.
    - The scope, deliverables, tech stack, roadmap, and pricing should all reflect the actual requirements described.
    - Do NOT use generic boilerplate — make everything specific to this project.
    - LEAN TEAM: Plan with the MINIMUM viable team. Prefer multi-skilled individuals who can cover multiple areas.
      For small-mid projects, 2-3 people should suffice (e.g., 1 Full-stack Developer, 1 Tech Lead who also does architecture/DevOps).
      Avoid listing separate roles for PM, QA, DevOps, etc. unless the project truly demands it. Keep it lean and cost-effective.

    Return a JSON object with:
    1. 'project_title': A short, professional project name derived from the actual requirement (e.g. 'Quiz & Certification Platform', 'Self-Ordering Kiosk System'). Do NOT use generic names like 'Digital Transformation'.
    2. 'hero_desc': A 1-2 sentence compelling description that references the actual project requirements.
    3. 'executive_summary': A professional overview of the project goals, summarizing the client's needs and the proposed solution.
    4. 'scope_of_work': Array of 4-5 key deliverables directly tied to the stated requirements.
    5. 'roadmap': Array of 3-4 phases. Each phase has:
        - 'phase': Name of the phase (e.g. 'Phase 1: Discovery & Architecture')
        - 'duration': Duration string (e.g. '2 Weeks', '3 Weeks') — ALWAYS include this.
        - 'details': Description of work done in this phase.
    6. 'total_duration': Total project duration as a string (e.g. '10–12 Weeks').
    7. 'pricing': Object with:
        - 'total': String — the total project cost in {currency} ONLY (e.g. '{"₹6,50,000" if currency == "INR" else "$7,500"}')
        - 'terms': String (e.g. '30% Advance, 40% Mid-way, 30% Deployment')
        - 'breakdown': Array of objects with 'item' (string) and 'cost' (string in {currency} ONLY, e.g. '{"₹1,00,000" if currency == "INR" else "$1,200"}').
          IMPORTANT: 'cost' MUST be a plain string like '{"₹1,00,000" if currency == "INR" else "$1,200"}', NOT a dict or object.
    8. 'resources': Array of 2-3 lean team members. Each object has 'role' (string) and 'allocation' (string like 'Full-time', 'Part-time', 'As needed').
    9. 'key_notes': Array of 3 important considerations specific to this project.
    10. 'tech_stack': Object with 'backend' (array) and 'data' (array).
    11. 'mermaid_diagram': A simple, valid Mermaid.js 'graph TD' string representing the architecture.
       USE ONLY SIMPLE TEXT IN QUOTES.
       Example: 'graph TD\\nA["User"] --> B["API"]\\nB --> C["DB"]'
    """
    try:
        response = client_ai.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Error: {e}")
        return None


def scrape_client(client_url):
    """Scrape client website for branding info."""
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
            if raw:
                client_data["name"] = raw[:40]

        logo = None
        og_image = soup.find("meta", property="og:image")
        if og_image:
            logo = urljoin(client_url, og_image.get("content"))
        if not logo:
            link = soup.find("link", rel=re.compile("icon", re.I))
            if link:
                logo = urljoin(client_url, link.get("href"))
        if logo:
            client_data["logo"] = logo

        theme_color = soup.find("meta", attrs={"name": "theme-color"})
        if theme_color:
            client_data["color"] = theme_color.get("content")
    except Exception as e:
        print(f"Scrape error: {e}")
    return client_data


def build_client_data(client_name, client_url=None):
    """Build client data dict — scrape if URL available, otherwise use name only."""
    if client_url:
        client_data = scrape_client(client_url)
        # Override scraped name with user-provided name if given
        if client_name:
            client_data["name"] = client_name
        return client_data
    else:
        return {
            "name": client_name or "Client",
            "url": None,
            "logo": None,
            "color": "#3B82F6",
        }


def generate_diagram(mermaid_code, output_dir="static"):
    """Generate diagram using mermaid-cli with explicit fallback to client-side rendering."""
    if not mermaid_code:
        print("[Mermaid] No code provided")
        return False

    os.makedirs(output_dir, exist_ok=True)
    mmd_path = os.path.abspath(os.path.join(output_dir, "temp.mmd"))
    out_path = os.path.abspath(os.path.join(output_dir, "architecture.png"))

    # Convert literal \n strings to actual newlines (AI often returns them as escaped)
    cleaned_code = mermaid_code.strip()
    cleaned_code = cleaned_code.replace("\\n", "\n")

    # Ensure graph TD is present
    if not any(cleaned_code.startswith(t) for t in ["graph", "flowchart", "sequenceDiagram"]):
        cleaned_code = "graph TD\n" + cleaned_code

    with open(mmd_path, "w") as f:
        f.write(cleaned_code)

    print(f"[Mermaid] Generating diagram from code:\n{cleaned_code}")

    try:
        cli_path = "./node_modules/.bin/mmdc"
        if os.path.exists(cli_path):
            cmd = [cli_path, "-i", mmd_path, "-o", out_path, "-b", "transparent", "-p", "puppeteer_config.json"]
        else:
            cmd = ["npx", "-y", "-p", "@mermaid-js/mermaid-cli", "mmdc", "-i", mmd_path, "-o", out_path, "-b",
                   "transparent"]

        # Create a basic puppeteer config to help with sandbox issues
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


def build_proposal(client_name=None, client_url=None, project_name=None,
                   brief_requirement=None, detailed_requirement=None,
                   currency="INR", app=None):
    """
    Build a proposal and save it with a unique ID.

    Args:
        client_name: Name of the client (required if no URL)
        client_url: Client website URL (optional)
        project_name: Name of the project (optional, auto-generated if missing)
        brief_requirement: Short project description from client
        detailed_requirement: Extracted text from uploaded/linked document
        currency: Preferred currency ('INR' or 'USD')
        app: Flask app instance for template rendering

    Returns:
        dict with template_data + proposal_id and proposal_url
    """
    # Build client data
    client_data = build_client_data(client_name, client_url)

    # Determine project name — use AI-generated title if available, fallback to provided name
    p_name = project_name if project_name else None  # Will be set after AI response

    # Generate unique proposal ID
    proposal_id = generate_proposal_id(client_data["name"])
    proposal_dir = os.path.join(PROPOSALS_DIR, proposal_id)
    os.makedirs(proposal_dir, exist_ok=True)

    # Generate AI content with all available context
    ai_content = get_ai_content(
        client_data["name"],
        p_name or f"{client_data['name']} Project",
        client_url=client_url,
        brief_requirement=brief_requirement,
        detailed_requirement=detailed_requirement,
        currency=currency
    )

    # Use AI-generated project title if no explicit name was given
    if not p_name and ai_content:
        p_name = ai_content.get("project_title", f"{client_data['name']} Project")
    elif not p_name:
        p_name = f"{client_data['name']} Project"

    # Try generating diagram into the proposal's directory
    diagram_ok = generate_diagram(
        ai_content.get("mermaid_diagram") if ai_content else None,
        output_dir=proposal_dir
    )

    template_data = {
        "client": client_data,
        "my_brand": MY_BRAND,
        "diagram_available": diagram_ok,
        "diagram_path": f"/static/proposals/{proposal_id}/architecture.png",
        "mermaid_code": ai_content.get("mermaid_diagram") if ai_content else None,
        "project_name": p_name,
        "ai": ai_content,
        "proposal_id": proposal_id,
        "generated_at": datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%B %d, %Y at %I:%M %p") + " IST",
    }

    if app:
        with app.app_context():
            html = render_template("proposal.html", **template_data)
    else:
        html = render_template("proposal.html", **template_data)

    # Save to unique proposal directory
    proposal_path = os.path.join(proposal_dir, "proposal.html")
    with open(proposal_path, "w") as f:
        f.write(html)

    # Also save to static/proposal.html for backward compatibility
    with open("static/proposal.html", "w") as f:
        f.write(html)

    # Update proposals index
    index_entry = add_to_index(proposal_id, client_data["name"], p_name, client_url)

    template_data["proposal_url"] = f"/proposal/{proposal_id}"
    return template_data
