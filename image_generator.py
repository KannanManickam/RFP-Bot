"""
Image generation module using OpenAI gpt-image-1.5 model.
Supports text-only generation and text + reference image editing.
"""

import os
import io
import base64
import uuid
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# Initialize OpenAI client (same env vars as generator.py)
client_ai = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

MODEL = "gpt-image-1.5"
GENERATED_DIR = os.path.join("static", "generated")
MAX_REFERENCE_IMAGES = 5
MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024  # 4MB per image (OpenAI limit)


def _ensure_output_dir():
    """Ensure the generated images directory exists."""
    os.makedirs(GENERATED_DIR, exist_ok=True)


def generate_image_from_text(prompt, size="1024x1024", quality="auto"):
    """
    Generate an image from a text prompt only.

    Args:
        prompt: Text description of the desired image.
        size: Output size (e.g., '1024x1024', '1536x1024', '1024x1536').
        quality: 'auto', 'high', or 'low'.

    Returns:
        dict with 'image_path', 'image_id', 'image_url' on success.
        None on failure.
    """
    try:
        response = client_ai.images.generate(
            model=MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

        # gpt-image-1 returns base64 by default
        image_b64 = response.data[0].b64_json
        if not image_b64:
            # Fallback: check for URL response
            image_url = response.data[0].url
            if image_url:
                import requests
                resp = requests.get(image_url, timeout=30)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode("utf-8")
            else:
                print("[ImageGen] No image data in response")
                return None

        return _save_image(image_b64, prompt)

    except Exception as e:
        print(f"[ImageGen] Text generation error: {e}")
        return None


def generate_image_with_references(prompt, image_data_list, size="1024x1024", quality="auto"):
    """
    Generate/edit an image using reference images + text prompt.

    Args:
        prompt: Text description of what to generate/modify.
        image_data_list: List of base64-encoded image strings or file-like objects.
        size: Output size.
        quality: 'auto', 'high', or 'low'.

    Returns:
        dict with 'image_path', 'image_id', 'image_url' on success.
        None on failure.
    """
    if not image_data_list:
        return generate_image_from_text(prompt, size, quality)

    try:
        # Prepare image inputs as file-like objects for the API
        image_files = []
        for i, img_b64 in enumerate(image_data_list[:MAX_REFERENCE_IMAGES]):
            img_bytes = base64.b64decode(img_b64)
            img_file = io.BytesIO(img_bytes)
            img_file.name = f"reference_{i}.png"
            image_files.append(img_file)

        # Use the first image as the primary, rest as additional context
        # images.edit accepts the image parameter
        response = client_ai.images.edit(
            model=MODEL,
            image=image_files if len(image_files) > 1 else image_files[0],
            prompt=prompt,
            size=size,
            n=1,
        )

        image_b64 = response.data[0].b64_json
        if not image_b64:
            image_url = response.data[0].url
            if image_url:
                import requests
                resp = requests.get(image_url, timeout=30)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode("utf-8")
            else:
                print("[ImageGen] No image data in edit response")
                return None

        return _save_image(image_b64, prompt)

    except Exception as e:
        print(f"[ImageGen] Reference image generation error: {e}")
        return None


def _save_image(image_b64, prompt=""):
    """
    Decode base64 image and save to disk.

    Returns:
        dict with 'image_path', 'image_id', 'image_url'.
    """
    _ensure_output_dir()

    image_id = _generate_image_id()
    filename = f"{image_id}.png"
    filepath = os.path.join(GENERATED_DIR, filename)

    image_bytes = base64.b64decode(image_b64)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    print(f"[ImageGen] Saved generated image: {filepath} ({len(image_bytes)} bytes)")

    return {
        "image_id": image_id,
        "image_path": filepath,
        "image_url": f"/image/{image_id}",
        "prompt": prompt[:200],  # Store truncated prompt for reference
    }


def _generate_image_id():
    """Generate a unique image ID with timestamp."""
    timestamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"img-{timestamp}-{short_uuid}"


def validate_image_size(file_size):
    """Check if an image file is within the size limit."""
    return file_size <= MAX_IMAGE_SIZE_BYTES
