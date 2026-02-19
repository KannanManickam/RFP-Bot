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
REFINE_MODEL = "gpt-5-nano"


def _ensure_output_dir():
    """Ensure the generated images directory exists."""
    os.makedirs(GENERATED_DIR, exist_ok=True)


def refine_prompt(user_prompt, has_reference_images=False):
    """
    Lightly refine the user's prompt for better image generation results.
    Keeps it short, concise, and faithful to the original intent.

    Returns:
        tuple of (refined_prompt, original_prompt)
    """
    if not user_prompt or len(user_prompt.strip()) < 3:
        return user_prompt, user_prompt

    context = (
        "with attached reference image(s)" if has_reference_images
        else "from scratch"
    )

    system_prompt = (
        "You are a prompt refiner for an AI image generator. "
        "The user will give you a rough image description. "
        "Your job is to LIGHTLY polish it into a better prompt.\n\n"
        "RULES:\n"
        "- Keep the SAME intent and subject — do NOT change what the user asked for.\n"
        "- Keep it SHORT and concise (1-3 sentences max).\n"
        "- Add subtle details like lighting, style, or composition ONLY if missing.\n"
        "- Do NOT over-embellish or add elements the user didn't mention.\n"
        "- Do NOT add quotation marks around your response.\n"
        "- Return ONLY the refined prompt text, nothing else.\n\n"
        f"Context: This image is being generated {context}."
    )

    try:
        response = client_ai.chat.completions.create(
            model=REFINE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
        )
        refined = response.choices[0].message.content.strip().strip('"').strip("'")
        if refined and len(refined) > 3:
            print(f"[ImageGen] Prompt refined: '{user_prompt}' -> '{refined}'")
            return refined, user_prompt
        return user_prompt, user_prompt
    except Exception as e:
        print(f"[ImageGen] Prompt refinement failed (using original): {e}")
        return user_prompt, user_prompt


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
        refined_prompt, original_prompt = refine_prompt(prompt, has_reference_images=False)

        response = client_ai.images.generate(
            model=MODEL,
            prompt=refined_prompt,
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

        return _save_image(image_b64, original_prompt, refined_prompt)

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
        refined_prompt, original_prompt = refine_prompt(prompt, has_reference_images=True)

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
            prompt=refined_prompt,
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

        return _save_image(image_b64, original_prompt, refined_prompt)

    except Exception as e:
        print(f"[ImageGen] Reference image generation error: {e}")
        return None


def _save_image(image_b64, original_prompt="", refined_prompt=""):
    """
    Decode base64 image and save to disk.

    Returns:
        dict with 'image_path', 'image_id', 'image_url', 'prompt', 'refined_prompt'.
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
        "prompt": original_prompt[:200],
        "refined_prompt": refined_prompt[:300],
    }


def _generate_image_id():
    """Generate a unique image ID with timestamp."""
    timestamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"img-{timestamp}-{short_uuid}"


def validate_image_size(file_size):
    """Check if an image file is within the size limit."""
    return file_size <= MAX_IMAGE_SIZE_BYTES
