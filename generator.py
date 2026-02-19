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
                   currency="INR", project_scale="Medium"):
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

    # Dynamic pricing configuration based on scale
    scale_map = {
        "Small": {
            "INR": ("₹50,000", "₹2,50,000", "₹1,50,000"),
            "USD": ("$1,000", "$5,000", "$3,000")
        },
        "Medium": {
            "INR": ("₹3,00,000", "₹10,00,000", "₹6,50,000"),
            "USD": ("$5,000", "$15,000", "$10,000")
        },
        "High": {
            "INR": ("₹12,00,000", "₹50,00,000", "₹25,00,000"),
            "USD": ("$20,000", "$100,000+", "$45,000")
        }
    }

    scale_key = project_scale.capitalize() if project_scale else "Medium"
    if scale_key not in scale_map:
        scale_key = "Medium"

    min_p, max_p, avg_p = scale_map[scale_key][currency]

    # Currency-specific pricing guidance
    if currency == "INR":
        pricing_guidance = (
            f"Use INR (Indian Rupees) ONLY. Use the ₹ symbol. "
            f"This is a {scale_key.upper()} scale project. "
            f"Typical range: {min_p} to {max_p}. Target around {avg_p} unless requirements dictate otherwise. "
            "Format amounts Indian style (e.g., ₹6,50,000)."
        )
    else:
        pricing_guidance = (
            f"Use USD (US Dollars) ONLY. Use the $ symbol. "
            f"This is a {scale_key.upper()} scale project. "
            f"Typical range: {min_p} to {max_p}. Target around {avg_p} unless requirements dictate otherwise. "
            "Format amounts US style (e.g., $7,500)."
        )

    prompt = f"""
    You are an expert Solution Architect and Deal Closer for 'Sparktoship'.
    Your goal is to write a WINNING technical proposal for a project named '{project_name}' for client '{client_name}'.

    CONTEXT PROVIDED:
    {context_block}

    PROJECT SCALE: {scale_key}
    PRICING GUIDANCE: {pricing_guidance}

    INSTRUCTIONS:
    1. **Be Consultant-First**: Don't just list features. Explain WHY they need it and HOW it solves a business problem.
    2. **Tailored & Specific**: specific features, specific tech stack choices, specific roadmap steps. Avoid generic fluff.
    3. **Dynamic Scope**:
       - If {scale_key} == 'Small': Focus on MVP, speed to market, core features only.
       - If {scale_key} == 'Medium': Balance robustness with speed. Standard professional web/mobile app features.
       - If {scale_key} == 'High': Focus on scalability, security, microservices, enterprise-grade architecture.
    4. **Pricing**:
       - MUST be in {currency}.
       - MUST align with the {scale_key} range provided ({min_p} - {max_p}).
       - Provide a realistic breakdown (Design, Dev, QA, Deployment, etc.).
    5. **Lean Team**:
       - Suggest a tight, efficient team structure appropriate for {scale_key} scale.

    OUTPUT FORMAT (JSON ONLY):
    {{
        "project_title": "Compelling, professional title (e.g., 'AI-Powered Logistics Platform')",
        "hero_desc": "1-2 powerful sentences selling the vision.",
        "executive_summary": "Professional summary of goals, needs, and solution (~3-4 sentences).",
        "scope_of_work": ["Deliverable 1 with detail", "Deliverable 2...", "Deliverable 3...", "Deliverable 4...", "Deliverable 5..."],
        "roadmap": [
            {{ "phase": "Phase 1: Name", "duration": "X Weeks", "details": "Key activities..." }},
            {{ "phase": "Phase 2: Name", "duration": "X Weeks", "details": "Key activities..." }}
        ],
        "total_duration": "e.g., '8–10 Weeks'",
        "pricing": {{
            "total": "Total Cost String (e.g., '₹6,50,000')",
            "terms": "Payment terms (e.g., '40% Upfront, 30% Milestone, 30% Completion')",
            "breakdown": [
               {{ "item": "Phase/Feature Name", "cost": "Cost String" }}
            ]
        }},
        "resources": [
            {{ "role": "e.g., Sr. Full Stack Dev", "allocation": "Full-time" }}
        ],
        "key_notes": ["Note 1", "Note 2", "Note 3"],
        "tech_stack": {{
            "backend": ["Tech 1", "Tech 2"],
            "frontend": ["Tech 1", "Tech 2"],
            "data": ["Tech 1"],
            "infrastructure": ["Tech 1"]
        }},
        "mermaid_diagram": "Simple graph TD string (e.g., 'graph TD\\nA[User] --> B[App]')"
    }}
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
        # Fallback to gpt-5-mini if nano fails
        try:
             response = client_ai.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
             return json.loads(response.choices[0].message.content)
        except Exception:
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
    
    # Remove markdown code blocks if present
    cleaned_code = re.sub(r'^```(?:mermaid)?', '', cleaned_code)
    cleaned_code = re.sub(r'```$', '', cleaned_code)
    
    cleaned_code = cleaned_code.strip()
    cleaned_code = cleaned_code.replace("\\n", "\n")
    
    # Remove 'mermaid' keyword if it appears at the start
    if cleaned_code.lower().startswith("mermaid"):
        cleaned_code = cleaned_code[7:].strip()

    # Ensure graph TD is present
    if not any(cleaned_code.startswith(t) for t in ["graph", "flowchart", "sequenceDiagram", "classDiagram", "erDiagram"]):
        cleaned_code = "graph TD\n" + cleaned_code
        
    # Extra safety: fix common syntax errors (like unquoted node names with spaces)
    # This is a basic heuristic: A[Node Name] -> A["Node Name"]
    # It finds patterns like [Some Text] and ensures it's ["Some Text"] if it contains spaces and isn't already quoted
    def quote_node_label(match):
        content = match.group(1)
        if '"' not in content and (' ' in content or '(' in content or ')' in content):
            return f'["{content}"]'
        return f'[{content}]'
        
    cleaned_code = re.sub(r'\[([^\]]+)\]', quote_node_label, cleaned_code)

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
                   currency="INR", project_scale="Medium", app=None):
    """
    Build a proposal and save it with a unique ID.

    Args:
        client_name: Name of the client (required if no URL)
        client_url: Client website URL (optional)
        project_name: Name of the project (optional, auto-generated if missing)
        brief_requirement: Short project description from client
        detailed_requirement: Extracted text from uploaded/linked document
        currency: Preferred currency ('INR' or 'USD')
        project_scale: Scale of the project ('Small', 'Medium', 'High')
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
        currency=currency,
        project_scale=project_scale
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
