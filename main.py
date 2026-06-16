import json
import logging
import os
import sys
import uuid
from typing import Optional, List, Dict
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFilter
import io
import re

if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google import genai
from google.genai import types
from livekit import api

from config import (
    LIVEKIT_AGENT_NAME,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_URL,
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
    cors_origins,
    validate_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("birthday-backend")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Birthday AI Adventure Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the generated_videos directory exists and mount it
generated_videos_dir = os.path.join(os.path.dirname(__file__), "generated_videos")
os.makedirs(generated_videos_dir, exist_ok=True)
app.mount("/generated_videos", StaticFiles(directory=generated_videos_dir), name="generated_videos")

# Ensure the generated_images directory exists and mount it
generated_images_dir = os.path.join(os.path.dirname(__file__), "generated_images")
os.makedirs(generated_images_dir, exist_ok=True)
app.mount("/generated_images", StaticFiles(directory=generated_images_dir), name="generated_images")


# Initialize Gemini Client
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini GenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")

from datetime import datetime

class LogRequest(BaseModel):
    password: str
    action: str

def log_activity(password: str, action: str):
    if password in ["manohari@123", "manohar@123"]:
        log_file_path = os.path.join(BASE_DIR, "user_activity.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {action}\n"
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.info(f"Logged activity: {action}")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")

@app.post("/api/log-action")
async def log_action(payload: LogRequest) -> dict:
    log_activity(payload.password, payload.action)
    return {"status": "success"}

@app.get("/api/gira-gira-music")
async def get_gira_gira():
    music_path = os.path.join(BASE_DIR, "Gira Gira.mp3")
    if os.path.exists(music_path):
        return FileResponse(music_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Music file not found")

class SessionRequest(BaseModel):
    name: Optional[str] = "Manohari"
    identity: Optional[str] = None
    stage: Optional[str] = "intro"

class ChatRequest(BaseModel):
    stage: str                  # "quiz", "wyr", "guess_fact"
    question: str
    answer: str
    history: Optional[List[Dict[str, str]]] = []

class ComplimentRequest(BaseModel):
    quiz_answers: List[Dict[str, str]]
    wyr_answers: List[Dict[str, str]]
    fact_answers: List[Dict[str, str]]

@app.on_event("startup")
def _startup_checks() -> None:
    missing = validate_config()
    if missing:
        logger.warning("Missing config: %s", ", ".join(missing))
    
    if gemini_client:
        try:
            models = [m.name for m in gemini_client.models.list()]
            image_models = [name for name in models if any(kw in name.lower() for kw in ['image', 'imagen'])]
            logger.info(f"Available Image Models for this key: {image_models}")
        except Exception as e:
            logger.error(f"Failed to list models: {e}")


@app.get("/health")
def health() -> dict:
    return {"ok": True}

def _build_token(room_name: str, identity: str, name: Optional[str]) -> str:
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity)
    if name:
        token.with_name(name)
    token.with_grants(api.VideoGrants(room_join=True, room=room_name))
    return token.to_jwt()

@app.post("/api/session")
async def create_session(payload: SessionRequest) -> dict:
    missing = validate_config()
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing configuration: {', '.join(missing)}",
        )

    room_name = f"birthday-{uuid.uuid4().hex[:10]}"
    identity = payload.identity or f"manohari-{uuid.uuid4().hex[:8]}"
    display_name = payload.name or "Manohari"

    token = _build_token(room_name, identity, display_name)

    lkapi = api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )
    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=LIVEKIT_AGENT_NAME,
                room=room_name,
                metadata=json.dumps({"source": "birthday_adventure", "stage": payload.stage}),
            )
        )
        logger.info(f"Dispatched agent '{LIVEKIT_AGENT_NAME}' to room '{room_name}' with stage '{payload.stage}'")
    except Exception as exc:
        logger.exception("LiveKit agent dispatch failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to start voice guide agent")
    finally:
        await lkapi.aclose()

    return {
        "room_name": room_name,
        "token": token,
        "livekit_url": LIVEKIT_URL,
        "agent_name": LIVEKIT_AGENT_NAME,
        "identity": identity,
        "name": display_name,
    }

@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict:
    if not gemini_client:
        return {"response": "That's super interesting! (Gemini API key is missing, but I support you anyway!)"}

    system_prompt = (
        "You are Aria, a magical, warm, and playful AI birthday guide created for Manohari's birthday.\n"
        f"We are currently in the '{payload.stage}' stage of her birthday game.\n"
        f"She was asked: '{payload.question}' and she answered: '{payload.answer}'.\n"
        "Give a quick, witty, and super enthusiastic reaction or comment (1-2 sentences max). "
        "Keep it fun, sweet, and focused on her response. Never be creepy, formal, or long-winded."
    )

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_CHAT_MODEL,
            contents=payload.answer,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9,
                max_output_tokens=150,
            )
        )
        return {"response": response.text.strip()}
    except Exception as e:
        logger.error(f"Gemini API chat error: {e}")
        return {"response": f"Oh, that's fabulous! I love that choice, Manohari! ✨"}

@app.post("/api/compliment")
async def generate_compliments(payload: ComplimentRequest) -> dict:
    if not gemini_client:
        return {
            "compliments": [
                "You have an amazing energy that lights up any space you enter!",
                "Your choices show a unique combination of creativity and adventurous spirit.",
                "You have a wonderful sense of fun and approach life with a beautiful curiosity!"
            ],
            "title": "A Spark of Magic"
        }

    prompt = (
        "Below are Manohari's answers to various personality, preference, and trivia questions from her Birthday Adventure:\n"
        f"Quiz answers: {json.dumps(payload.quiz_answers)}\n"
        f"Would-You-Rather answers: {json.dumps(payload.wyr_answers)}\n"
        f"Trivia results: {json.dumps(payload.fact_answers)}\n\n"
        "Write 3 short, deeply positive, and personalized compliments or insights about her personality based on these inputs. "
        "Each compliment should be 1-2 sentences, warm, uplifting, and creative. "
        "Format the output strictly as a JSON object with two fields:\n"
        "1. 'title': A sweet, magical title summarizing her vibe (e.g. 'The Starlit Explorer' or 'The Cosmic Dreamer')\n"
        "2. 'compliments': A list of exactly 3 strings (the compliments).\n"
        "Do NOT include markdown formatting like ```json or anything else. Just the raw JSON string."
    )

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text.strip())
        return data
    except Exception as e:
        logger.error(f"Gemini API compliment error: {e}")
        return {
            "compliments": [
                "You are naturally curious, choosing paths that favor adventure and growth.",
                "You possess a warm and creative spirit that makes every game and interaction feel like a celebration.",
                "Your decisions reflect a thoughtful, fun-loving approach to life that is truly inspiring."
            ],
            "title": "The Spark of Joy"
        }

@app.post("/api/final-message")
async def generate_final_message(payload: ComplimentRequest) -> dict:
    if not gemini_client:
        return {
            "title": "Your Adventure Profile: Cosmic Dreamer",
            "profile": "A wonderful soul who loves adventure, brings joy to others, and makes the world a brighter place.",
            "wishes": "May this birthday bring you infinite laughter, beautiful journeys, and dreams fulfilled. Have a gorgeous year!"
        }

    prompt = (
        "Based on Manohari's game choices:\n"
        f"Quiz: {json.dumps(payload.quiz_answers)}\n"
        f"Would You Rather: {json.dumps(payload.wyr_answers)}\n"
        "Generate a magical birthday profile summary for her. "
        "Return a JSON object containing:\n"
        "1. 'title': A fun title like 'Your Birthday Character Profile: The Dream Chaser'\n"
        "2. 'profile': A short paragraph (3-4 sentences) summarizing her personality type based on her game selections in a fun, positive, story-like way.\n"
        "3. 'wishes': A warm birthday wish wishing her a fantastic year ahead.\n"
        "Do NOT include markdown formatting. Return raw JSON."
    )

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text.strip())
        return data
    except Exception as e:
        logger.error(f"Gemini API final-message error: {e}")
        return {
            "title": "Your Birthday Profile: The Spirited Explorer",
            "profile": "A vibrant personality who pairs classic style with a love for high-spirited adventures. You are creative, thoughtful, and bring a special touch of magic wherever you go.",
            "wishes": "Manohari, may this year bring you closer to all your biggest dreams and fill every day with joy, laughter, and wonder! Happy Birthday!"
        }

class SurpriseRequest(BaseModel):
    landscape: str
    dress: str
    color: str
    password: Optional[str] = None

@app.post("/api/generate-surprise")
async def generate_surprise(payload: SurpriseRequest) -> dict:
    if not gemini_client:
        return {"status": "error", "message": "Gemini API key is not configured"}

    source_image_path = os.path.join(BASE_DIR, "pictures", "WhatsApp Image 2026-06-11 at 11.27.01.jpeg")
    output_image_path = os.path.join(BASE_DIR, "generated_images", "surprise_generated.png")

    if not os.path.exists(source_image_path):
      logger.error(f"Source image not found at {source_image_path}")
      return {"status": "error", "message": "Source image not found"}

    log_activity(payload.password, f"Requested generation of portrait 1 (Landscape: {payload.landscape}, Dress: {payload.dress}, Color: {payload.color})")

    try:
        # Step 1: Open the source image
        src_img = Image.open(source_image_path)
        
        # Step 2: Construct prompt
        dress_clean = payload.dress.replace("🥻 ", "").replace("👗 ", "").replace("💃 ", "").replace("✍️ ", "").replace("Custom: ", "")
        color_clean = payload.color.replace("⚪ ", "").replace("🌸 ", "").replace("🔵 ", "").replace("✍️ ", "").replace("Custom: ", "")
        landscape_clean = payload.landscape.replace("🌊 ", "").replace("🏔️ ", "").replace("🌆 ", "").replace("🌲 ", "")
        
        logger.info(f"Generating aesthetic background for landscape={landscape_clean}, dress={dress_clean}, color={color_clean}...")
        prompt_text = (
            f"Based on the person in the input photo, generate a high-quality, extremely professional starlit aesthetic studio portrait photograph of this exact same woman. "
            f"She should be standing in a setting with {landscape_clean}, wearing a gorgeous {color_clean} {dress_clean}. "
            f"Maintain her facial structure, look, hair, and features so it looks exactly like the person in the input photo. "
            f"Close-up portrait view, centered composition, aesthetic soft lighting, highly detailed, looking forward. "
            f"Do not add any text or watermark to the image."
        )
        
        # Step 3: Call Gemini multimodal image generator (which accepts image inputs)
        logger.info("Calling generate_content with gemini-3.1-flash-image...")
        generated_bytes = None
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=[src_img, prompt_text]
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    generated_bytes = part.inline_data.data
                    break
        except Exception as e:
            logger.warning(f"Failed to generate using gemini-3.1-flash-image: {e}. Trying fallback model gemini-2.5-flash-image...")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[src_img, prompt_text]
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    generated_bytes = part.inline_data.data
                    break
        
        if not generated_bytes:
            raise ValueError("No image bytes were returned by the Gemini image generator model")
        
        gen_img = Image.open(io.BytesIO(generated_bytes))
        
        # Step 4: Save the final generated image to public folder
        os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
        gen_img.save(output_image_path, "PNG")
        logger.info(f"Successfully generated and saved image to {output_image_path}")
        log_activity(payload.password, f"Successfully generated and saved portrait 1 image to /generated_images/surprise_generated.png using prompt: {prompt_text}")
        
        return {"status": "success", "url": "/generated_images/surprise_generated.png"}
        
    except Exception as e:
        logger.error(f"Error in generate_surprise: {e}")
        log_activity(payload.password, f"Failed to generate portrait 1 image. Saved source image as fallback. Error: {str(e)}")
        # In case of any error, save a copy of the original image as fallback
        try:
            os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
            src_img.save(output_image_path, "PNG")
            logger.info("Saved source image as fallback surprise image")
            return {"status": "success", "url": "/generated_images/surprise_generated.png", "fallback": True}
        except Exception as fallback_err:
            logger.error(f"Fallback save failed: {fallback_err}")
            return {"status": "error", "message": str(e)}


class SurpriseRequest2(BaseModel):
    backdrop: str
    outfit: str
    aesthetic_color: str
    password: Optional[str] = None

@app.post("/api/generate-surprise-2")
async def generate_surprise_2(payload: SurpriseRequest2) -> dict:
    if not gemini_client:
        return {"status": "error", "message": "Gemini API key is not configured"}

    source_image_path = os.path.join(BASE_DIR, "pictures", "WhatsApp Image 2026-06-11 at 11.27.01.jpeg")
    output_image_path = os.path.join(BASE_DIR, "generated_images", "surprise_generated_2.png")

    if not os.path.exists(source_image_path):
        logger.error(f"Source image not found at {source_image_path}")
        return {"status": "error", "message": "Source image not found"}

    log_activity(payload.password, f"Requested generation of portrait 2 (Backdrop: {payload.backdrop}, Outfit: {payload.outfit}, Color: {payload.aesthetic_color})")

    try:
        # Step 1: Open the source image
        src_img = Image.open(source_image_path)
        
        # Step 2: Clean parameters
        outfit_clean = re.sub(r'[^\w\s\-\,\.\(\)]', '', payload.outfit).replace("Custom", "").replace("Type your own", "").strip()
        color_clean = re.sub(r'[^\w\s\-\,\.\(\)]', '', payload.aesthetic_color).replace("Custom", "").replace("Type your own", "").strip()
        backdrop_clean = re.sub(r'[^\w\s\-\,\.\(\)]', '', payload.backdrop).strip()

        logger.info(f"Generating aesthetic background 2 for backdrop={backdrop_clean}, outfit={outfit_clean}, color={color_clean}...")
        prompt_text = (
            f"Based on the person in the input photo, generate a high-quality, extremely professional starlit aesthetic studio portrait photograph of this exact same woman. "
            f"She should be standing in a setting with {backdrop_clean}, wearing a gorgeous {color_clean} {outfit_clean}. "
            f"Maintain her facial structure, look, hair, and features so it looks exactly like the person in the input photo. "
            f"Close-up portrait view, centered composition, aesthetic soft lighting, highly detailed, looking forward. "
            f"Do not add any text or watermark to the image."
        )
        
        # Step 3: Call Gemini multimodal image generator
        logger.info("Calling generate_content for second portrait using gemini-3.1-flash-image...")
        generated_bytes = None
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=[src_img, prompt_text]
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    generated_bytes = part.inline_data.data
                    break
        except Exception as e:
            logger.warning(f"Failed to generate using gemini-3.1-flash-image: {e}. Trying fallback model gemini-2.5-flash-image...")
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[src_img, prompt_text]
            )
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    generated_bytes = part.inline_data.data
                    break
        
        if not generated_bytes:
            raise ValueError("No image bytes were returned by the Gemini image generator model")
        
        gen_img = Image.open(io.BytesIO(generated_bytes))
        
        # Step 4: Save the final generated image
        os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
        gen_img.save(output_image_path, "PNG")
        logger.info(f"Successfully generated and saved second image to {output_image_path}")
        log_activity(payload.password, f"Successfully generated and saved portrait 2 image to /generated_images/surprise_generated_2.png using prompt: {prompt_text}")
        
        return {"status": "success", "url": "/generated_images/surprise_generated_2.png"}
        
    except Exception as e:
        logger.error(f"Error in generate_surprise_2: {e}")
        log_activity(payload.password, f"Failed to generate portrait 2 image. Saved source image as fallback. Error: {str(e)}")
        try:
            os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
            src_img.save(output_image_path, "PNG")
            logger.info("Saved source image as fallback second surprise image")
            return {"status": "success", "url": "/generated_images/surprise_generated_2.png", "fallback": True}
        except Exception as fallback_err:
            logger.error(f"Fallback save failed for image 2: {fallback_err}")
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)

