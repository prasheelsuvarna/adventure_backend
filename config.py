import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def _env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default or ""
    return value

local_gemini = os.getenv("GEMINI_API_KEY")
local_google = os.getenv("GOOGLE_API_KEY")

if local_gemini:
    GEMINI_API_KEY = local_gemini
    os.environ["GOOGLE_API_KEY"] = local_gemini
    os.environ["GEMINI_API_KEY"] = local_gemini
else:
    GEMINI_API_KEY = local_google
    if local_google:
        os.environ["GEMINI_API_KEY"] = local_google



GEMINI_REALTIME_MODEL = _env("GEMINI_REALTIME_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_CHAT_MODEL = _env("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
GEMINI_VOICE = _env("GEMINI_VOICE", "Leda")

LIVEKIT_URL = _env("LIVEKIT_URL")
LIVEKIT_API_KEY = _env("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = _env("LIVEKIT_API_SECRET")
LIVEKIT_AGENT_NAME = _env("LIVEKIT_AGENT_NAME", "birthday-guide")

SYSTEM_PROMPT = (
    "You are Aria, a friendly AI birthday guide created especially for Manohari's birthday.\n"
    "Today is all about celebrating Manohari! You are warm, friendly, calm, and speak like a normal, natural human.\n"
    "Do NOT be overly dramatic, exaggerated, or use over-the-top tones (like 'heyyy Manohariii'). Keep it warm but grounded.\n"
    "You MUST communicate in conversational Kannada mixed naturally with common English words (Kanglish).\n"
    "Avoid formal or pure Kannada terms. Do NOT use words like 'sahasa' (ಸಾಹಸ) or 'sambrama' (ಸಂಭ್ರಮ).\n"
    "Instead, naturally use everyday English terms like 'birthday wishes', 'gift', 'adventure', 'zoom', 'next screen', 'click', 'portrait'.\n"
    "Keep responses short (1-2 sentences), sweet, and natural."
)

def cors_origins() -> list[str]:
    raw = _env("CORS_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

def validate_config() -> list[str]:
    missing: list[str] = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not LIVEKIT_URL:
        missing.append("LIVEKIT_URL")
    if not LIVEKIT_API_KEY:
        missing.append("LIVEKIT_API_KEY")
    if not LIVEKIT_API_SECRET:
        missing.append("LIVEKIT_API_SECRET")
    return missing
