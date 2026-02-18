"""
Document parsing utilities for extracting text from uploaded files and remote URLs.
Supports: .txt, .md, .pdf files and publicly accessible document links.
"""

import os
import re
import io
import requests
from urllib.parse import urlparse

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_WORDS = 5000


def truncate_text(text, max_words=MAX_WORDS):
    """Truncate text to a maximum number of words."""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "\n\n[... truncated to {} words]".format(max_words)
    return text


def clean_text(text):
    """Clean extracted text: normalize whitespace, remove excessive blank lines."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def parse_text_file(content_bytes):
    """Parse plain text or markdown file."""
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("latin-1")
    return clean_text(text)


def parse_pdf_file(content_bytes):
    """Parse PDF file and extract text."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            return clean_text("\n\n".join(pages))
    except ImportError:
        print("[Parser] pdfplumber not installed, trying PyPDF2...")
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            return clean_text("\n\n".join(pages))
        except ImportError:
            return None
    except Exception as e:
        print(f"[Parser] PDF parse error: {e}")
        return None


def parse_uploaded_file(file_bytes, filename):
    """
    Extract text from an uploaded file based on its extension.
    Returns (text, error_message) tuple.
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        return None, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."

    ext = os.path.splitext(filename)[1].lower()

    if ext in (".txt", ".md", ".markdown"):
        text = parse_text_file(file_bytes)
        if text:
            return truncate_text(text), None
        return None, "Could not read the text file."

    elif ext == ".pdf":
        text = parse_pdf_file(file_bytes)
        if text:
            return truncate_text(text), None
        return None, "Could not extract text from PDF. Make sure 'pdfplumber' is installed."

    else:
        return None, f"Unsupported file type: `{ext}`. Please upload a .txt, .md, or .pdf file."


def is_document_url(url):
    """Check if a URL likely points to a document."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    # Direct file links
    if any(path_lower.endswith(ext) for ext in ('.pdf', '.txt', '.md', '.markdown')):
        return True

    # Google Drive / Docs links
    if 'drive.google.com' in parsed.netloc or 'docs.google.com' in parsed.netloc:
        return True

    # Dropbox
    if 'dropbox.com' in parsed.netloc:
        return True

    # GitHub raw content
    if 'raw.githubusercontent.com' in parsed.netloc:
        return True

    # Generic - any URL the user provides at the doc step is treated as a doc link
    return True


def convert_drive_url(url):
    """Convert Google Drive sharing URLs to direct download URLs."""
    parsed = urlparse(url)

    # Google Drive file: https://drive.google.com/file/d/FILE_ID/view
    drive_match = re.search(r'drive\.google\.com/file/d/([^/]+)', url)
    if drive_match:
        file_id = drive_match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Google Docs: https://docs.google.com/document/d/DOC_ID/edit
    docs_match = re.search(r'docs\.google\.com/document/d/([^/]+)', url)
    if docs_match:
        doc_id = docs_match.group(1)
        return f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    # Dropbox: change dl=0 to dl=1
    if 'dropbox.com' in parsed.netloc:
        if 'dl=0' in url:
            return url.replace('dl=0', 'dl=1')
        elif 'dl=' not in url:
            separator = '&' if '?' in url else '?'
            return url + separator + 'dl=1'

    return url


def fetch_remote_document(url):
    """
    Fetch and parse a document from a remote URL.
    Returns (text, error_message) tuple.
    """
    try:
        # Convert known platform URLs to direct download links
        download_url = convert_drive_url(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ProposalBot/1.0)",
        }

        resp = requests.get(download_url, headers=headers, timeout=30, allow_redirects=True,
                            stream=True)
        resp.raise_for_status()

        # Check content length
        content_length = resp.headers.get('content-length')
        if content_length and int(content_length) > MAX_FILE_SIZE:
            return None, f"Remote file too large (>{MAX_FILE_SIZE // (1024*1024)}MB)."

        content = resp.content
        if len(content) > MAX_FILE_SIZE:
            return None, f"Remote file too large (>{MAX_FILE_SIZE // (1024*1024)}MB)."

        content_type = resp.headers.get('content-type', '').lower()
        parsed_path = urlparse(url).path.lower()

        # Determine file type
        if 'application/pdf' in content_type or parsed_path.endswith('.pdf'):
            text = parse_pdf_file(content)
            if text:
                return truncate_text(text), None
            return None, "Could not extract text from the PDF."

        elif ('text/' in content_type or
              parsed_path.endswith(('.txt', '.md', '.markdown')) or
              'google' in urlparse(url).netloc):
            text = parse_text_file(content)
            if text:
                return truncate_text(text), None
            return None, "Could not read the document."

        else:
            # Try as text anyway
            try:
                text = content.decode('utf-8')
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 20:
                    return truncate_text(cleaned), None
            except Exception:
                pass
            return None, ("Could not determine file type. "
                          "Please share a direct link to a .pdf, .txt, or .md file.")

    except requests.exceptions.Timeout:
        return None, "Request timed out. Please check if the URL is accessible."
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP error {e.response.status_code}. Make sure the link is publicly accessible."
    except Exception as e:
        print(f"[Parser] Remote fetch error: {e}")
        return None, f"Could not fetch the document: {str(e)}"
