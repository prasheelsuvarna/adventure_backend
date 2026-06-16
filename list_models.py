"""Quick script to list all available Gemini models for this API key."""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

print("=== All available models ===\n")
image_models = []
for model in client.models.list():
    name = model.name
    # Flag image-capable models
    is_image = any(kw in name.lower() for kw in ['image', 'imagen', 'flash-exp', 'vision'])
    marker = "  🖼️  IMAGE" if is_image else ""
    print(f"  {name}{marker}")
    if is_image:
        image_models.append(name)

print("\n=== Models likely supporting image generation ===")
for m in image_models:
    print(f"  {m}")
