"""
╔══════════════════════════════════════════════════════════════════════╗
║         MOON & SUN POETIC VIDEO GENERATOR  –  Veo 2 API            ║
║                                                                      ║
║  Generates two ~30-second cinematic poetry videos:                   ║
║   • moon_video.mp4  →  "You are the only moon I notice…"            ║
║   • sun_video.mp4   →  "I would stare at you until I lose vision…"  ║
║                                                                      ║
║  HOW TO RUN:                                                         ║
║   1. pip install moviepy google-genai pillow                         ║
║   2. Put the Gira Gira song as  gira_gira.mp3  in this folder        ║
║   3. python generate_videos.py                                       ║
║                                                                      ║
║  Output: generated_videos/moon_video.mp4                            ║
║          generated_videos/sun_video.mp4                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import base64
import shutil
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────
PICTURES_DIR = Path(__file__).parent / "pictures"
OUTPUT_DIR   = Path(__file__).parent / "generated_videos"
CLIPS_DIR    = Path(__file__).parent / "generated_clips"
SONG_PATH    = Path(__file__).parent / "Gira Gira.mp3"     # place your mp3 here
PROGRESS_FILE = Path(__file__).parent / "video_gen_progress.json"

VEO_MODEL    = "veo-2.0-generate-001"
CLIP_DURATION = 8      # seconds per clip (Veo 2 max = 8)
ASPECT_RATIO  = "16:9"

# ──────────────────────────────────────────────────────────────────────
# CORRECTED POETIC LINES (grammar fixed)
# ──────────────────────────────────────────────────────────────────────
MOON_POEM = (
    "In a sky full of stars, you are the only moon I notice. "
    "Unfortunately, I am too poor to build a rocket to reach you. "
    "I hope someday I will ascend and reach you."
)

SUN_POEM = (
    "If you were the sun I would continue to stare at you. "
    "Even if it costs my vision for i would know the last thing I saw was perfection."
)

# ──────────────────────────────────────────────────────────────────────
# BEST REFERENCE PHOTOS (chosen for variety & quality)
# ──────────────────────────────────────────────────────────────────────
PORTRAIT_PHOTOS = [
    "WhatsApp Image 2026-06-11 at 11.27.22.jpeg",   # boat, river background (Index 0)
    "WhatsApp Image 2026-06-11 at 11.27.01.jpeg",   # blue anarkali dress, full body
    "WhatsApp Image 2026-06-11 at 11.26.56.jpeg",   # close portrait, warm garden
    "WhatsApp Image 2026-06-11 at 11.27.00.jpeg",   # rooftop, dupatta, sky behind
    "WhatsApp Image 2026-06-11 at 11.27.19.jpeg",   # garden, natural light
]

# ──────────────────────────────────────────────────────────────────────
# CINEMATIC SCENE PROMPTS
# ──────────────────────────────────────────────────────────────────────
# Each entry: {type, prompt, photo_key (optional)}
# type: "text" = text-to-video   |   "image" = image-to-video (uses photo_key index)

MOON_SCENES = [
    {
        "id": "moon_01",
        "type": "text",
        "prompt": (
            "Cinematic medium shot: A young Indian man, shown only as a dark, faceless silhouette, "
            "stands alone on a rooftop at night. He reaches one arm slowly upward toward the huge, "
            "glowing full moon that hangs impossibly high and bright in the starry sky. "
            "Stars shimmer. A soft wind moves his shirt. His posture radiates longing, "
            "admiration, and quiet heartbreak. Deep blue-black tones, cinematic, emotional, "
            "no text, no face visible, poetic and melancholic. 8K."
        ),
        "photo_index": None,
    },
    {
        "id": "moon_02",
        "type": "text",
        "prompt": (
            "Cinematic slow push-in to the surface of the glowing full moon. The craters on the moon slowly "
            "dissolve and transform into the beautiful face of the young Indian woman, appearing like a "
            "mystical Moon Princess looking down from within the lunar surface. Her eyes are warm and gentle, "
            "gazing down lovingly with a soft, ethereal smile. Moonlight bathes her features. "
            "Magical realism, dreamy silver-blue light, 8K, cinematic. No text."
        ),
        "photo_index": None,
    },
    {
        "id": "moon_03",
        "type": "text",
        "prompt": (
            "Cinematic shot: A young Indian man, seen as a dark silhouette, attempts to climb a glowing, "
            "magical staircase of pure starlight reaching high into the night sky toward the full moon. "
            "Suddenly, the stairs of starlight flicker and vanish under his feet, and he loses his grip, "
            "falling downward into the dark night sky. Cinematic slow motion, dramatic, dreamy blue and "
            "black color grade. 8K. No text."
        ),
        "photo_index": None,
    },
    {
        "id": "moon_04",
        "type": "text",
        "prompt": (
            "Cinematic shot: The dark, faceless silhouette of a young Indian man wearing a simple shirt "
            "attempts to climb a steep, misty dreamlike mountain peak reaching toward the giant glowing moon. "
            "Suddenly, the rocks crumble under his feet, and he falls downward a second time, tumbling into "
            "the soft cosmic mist below. Cinematic slow motion, emotional, dramatic, deep dark blue tones, "
            "poetic and tragic. 8K. No text."
        ),
        "photo_index": None,
    },
    {
        "id": "moon_05",
        "type": "text",
        "prompt": (
            "Cinematic final scene: The dark, faceless silhouette of the young Indian man sits on the ground, "
            "head lowered in defeat as he gives up. Behind him, a brilliant silver light descends. "
            "The beautiful Moon Princess (with long dark hair, wearing a flowing silver-white saree) "
            "gently lands on the ground behind him, walking toward him as a warm magical silver glow "
            "envelops them. Romantic, magical realism, happy ending. 8K cinematic. No text."
        ),
        "photo_index": None,
    },
]

SUN_SCENES = [
    {
        "id": "sun_01",
        "type": "text",
        "prompt": (
            "Cinematic wide shot: a blazing golden sunrise erupts magnificently over misty mountain peaks. "
            "Warm amber, orange, and deep gold tones saturate the frame. "
            "A beautiful, slender young Indian woman with long dark hair stands in an open field "
            "below, arms slightly open, face tilted upward toward the rising sun. "
            "Her flowing golden-orange dupatta billows behind her. "
            "Morning golden light falls on her, making her glow like a goddess. "
            "Slow cinematic push-forward. 8K, warm golden-hour color grade, romantic and breathtaking. "
            "No text overlays."
        ),
        "photo_index": None,
    },
    {
        "id": "sun_02",
        "type": "image",
        "prompt": (
            "Cinematic transformation: warm golden sunrise light floods across the face of "
            "the beautiful young Indian woman. Her eyes catch the fire of the rising sun, "
            "glowing with amber and gold. She closes her eyes slowly, feeling the warmth, "
            "a serene and radiant smile forming on her lips. Slow motion. "
            "Golden light halos her dark hair. Bokeh warm light particles float around her. "
            "8K, warm golden color grade, breathtaking and cinematic. No text. No logo."
        ),
        "photo_index": 0,   # portrait
    },
    {
        "id": "sun_03",
        "type": "text",
        "prompt": (
            "Cinematic medium shot from behind: a young Indian man, shown only as a dark silhouette, "
            "stands alone in a vast open field at golden hour. He faces the blazing sun directly, "
            "staring at it without flinching — refusing to look away. "
            "His silhouette is dramatic, backlit by blinding golden-white solar light. "
            "His arms hang at his side, posture conveying quiet, stubborn devotion. "
            "The sun dominates the frame above him. Warm amber and orange tones. "
            "Cinematic, emotional, 8K. No face visible. No text."
        ),
        "photo_index": None,
    },
    {
        "id": "sun_04",
        "type": "image",
        "prompt": (
            "Cinematic slow motion: the beautiful young Indian woman walks forward through "
            "a golden wheat or flower field. Sunlight halos her dark hair brilliantly. "
            "She glances back over her shoulder with a soft, fleeting smile. "
            "Golden particles and pollen float lazily in the warm air around her. "
            "Every frame is drenched in warm amber and golden-hour light. "
            "8K, cinematic, breathtakingly beautiful. No text."
        ),
        "photo_index": 0,   # portrait
    },
    {
        "id": "sun_05",
        "type": "text",
        "prompt": (
            "Cinematic wide golden shot: the blazing sun slowly sets over the horizon, "
            "painting the sky in magnificent layers of deep orange, crimson, and gold. "
            "The silhouette of the young Indian woman stands against the setting sun, "
            "arms slightly open, ethereal — as if she IS the sun itself. "
            "The faceless silhouette of a young man watches her from a foreground hill, "
            "unmoving, unwavering, gazing until the very last ray of light vanishes. "
            "Slow fade to warm amber, then to golden black. "
            "8K cinematic, emotional, poetic. No text. Ends on darkness."
        ),
        "photo_index": None,
    },
]


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_photo_bytes(photo_index: int) -> bytes:
    photo_name = PORTRAIT_PHOTOS[photo_index]
    photo_path = PICTURES_DIR / photo_name
    if not photo_path.exists():
        raise FileNotFoundError(f"Photo not found: {photo_path}")
    with open(photo_path, "rb") as f:
        return f.read()

def print_banner(text: str, char: str = "═"):
    width = 66
    print(f"\n╔{char * (width - 2)}╗")
    for line in text.split("\n"):
        print(f"║  {line:<{width - 4}}║")
    print(f"╚{char * (width - 2)}╝\n")


# ══════════════════════════════════════════════════════════════════════
# VIDEO GENERATION
# ══════════════════════════════════════════════════════════════════════

def generate_clip(client, scene: dict, output_path: Path) -> bool:
    """Generate a single video clip using Veo API. Returns True on success."""
    from google.genai import types

    print(f"  🎬  Generating clip: {scene['id']}")
    print(f"       Type   : {'image-to-video' if scene['type'] == 'image' else 'text-to-video'}")
    print(f"       Prompt : {scene['prompt'][:80]}…\n")

    config = types.GenerateVideosConfig(
        aspect_ratio=ASPECT_RATIO,
        number_of_videos=1,
        duration_seconds=CLIP_DURATION,
    )

    try:
        if scene["type"] == "image" and scene.get("photo_index") is not None:
            img_bytes = get_photo_bytes(scene["photo_index"])
            operation = client.models.generate_videos(
                model=VEO_MODEL,
                prompt=scene["prompt"],
                image=types.Image(
                    image_bytes=img_bytes,
                    mime_type="image/jpeg",
                ),
                config=config,
            )
        else:
            operation = client.models.generate_videos(
                model=VEO_MODEL,
                prompt=scene["prompt"],
                config=config,
            )
    except Exception as e:
        print(f"  ❌  API error starting generation: {e}")
        return False

    # Poll until done
    print("  ⏳  Waiting for Veo API (this takes ~2-5 mins per clip)…")
    poll_count = 0
    while not operation.done:
        time.sleep(20)
        poll_count += 1
        try:
            operation = client.operations.get(operation)
        except Exception as e:
            print(f"  ⚠️  Poll error (will retry): {e}")
            time.sleep(10)
        if poll_count % 3 == 0:
            elapsed = poll_count * 20
            print(f"       Still processing… ({elapsed}s elapsed)")

    if not operation.response or not operation.response.generated_videos:
        print(f"  ❌  No video generated. Check API quota / content filters.")
        return False

    # Download and save
    try:
        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save(str(output_path))
        print(f"  ✅  Saved → {output_path.name}")
        return True
    except Exception as e:
        print(f"  ❌  Error saving clip: {e}")
        return False


def generate_all_clips(client, scenes: list, prefix: str, progress: dict) -> list[Path]:
    """Generate all clips for a video theme, skipping already-done ones."""
    clip_paths = []
    CLIPS_DIR.mkdir(exist_ok=True)

    for scene in scenes:
        clip_path = CLIPS_DIR / f"{scene['id']}.mp4"

        if progress.get(scene["id"]) == "done" and clip_path.exists():
            print(f"  ✅  Skipping (already generated): {scene['id']}")
            clip_paths.append(clip_path)
            continue

        success = generate_clip(client, scene, clip_path)

        if success:
            progress[scene["id"]] = "done"
            save_progress(progress)
            clip_paths.append(clip_path)
        else:
            print(f"  ⚠️  Skipping failed clip {scene['id']} — will generate without it")

    return clip_paths


# ══════════════════════════════════════════════════════════════════════
# VIDEO STITCHING  (moviepy)
# ══════════════════════════════════════════════════════════════════════

def stitch_video(clip_paths: list[Path], output_path: Path, poem_text: str, song_path: Path = None):
    """Stitch clips, add poem text overlay, and optionally mix the Gira Gira audio.
    Compatible with moviepy v2.x (with_audio, with_volume_scaled, subclipped, etc.)
    """
    try:
        from moviepy import (
            VideoFileClip, concatenate_videoclips,
            AudioFileClip, CompositeAudioClip,
            TextClip, CompositeVideoClip,
            concatenate_audioclips,
        )
        from moviepy import vfx
    except ImportError:
        print("  ❌  moviepy not installed. Run: pip install moviepy")
        return False

    print(f"\n  🎞️   Stitching {len(clip_paths)} clips into {output_path.name}…")

    # Load clips
    clips = []
    for cp in clip_paths:
        try:
            clips.append(VideoFileClip(str(cp)))
        except Exception as e:
            print(f"  ⚠️  Couldn't load {cp.name}: {e}")

    if not clips:
        print("  ❌  No clips to stitch!")
        return False

    final_clip = concatenate_videoclips(clips, method="compose")

    # ── Audio ───────────────────────────────────────────────────────
    audio_tracks = []

    # Existing ambient audio from generated clips
    if final_clip.audio:
        audio_tracks.append(final_clip.audio.with_volume_scaled(0.3))

    # Gira Gira background music
    if song_path and song_path.exists():
        print(f"  🎵  Adding Gira Gira background track…")
        try:
            music = AudioFileClip(str(song_path))
            # Loop music to cover full video length if shorter
            if music.duration < final_clip.duration:
                loops = int(final_clip.duration / music.duration) + 1
                music = concatenate_audioclips([music] * loops)
            music = music.subclipped(32, 32 + final_clip.duration).with_volume_scaled(0.75)
            audio_tracks.append(music)
        except Exception as e:
            print(f"  ⚠️  Could not load song: {e}")
    else:
        print(f"  ℹ️  No gira_gira.mp3 found → video will have ambient audio only")
        print(f"       (Place gira_gira.mp3 next to this script to add music)")

    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        final_clip = final_clip.with_audio(final_audio)

    # ── Poem text overlay (last 7 seconds) ─────────────────────────
    try:
        words = poem_text.split()
        mid   = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        display_text = f"{line1}\n{line2}"

        txt_start    = max(0, final_clip.duration - 7)
        txt_duration = min(7.0, final_clip.duration)

        txt = (
            TextClip(
                text=display_text,
                font_size=36,
                color="white",
                font="DejaVu-Sans",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(int(final_clip.w * 0.8), None),
                text_align="center",
            )
            .with_start(txt_start)
            .with_duration(txt_duration)
            .with_position("center")
            .with_effects([vfx.CrossFadeIn(1.5)])
        )

        final_clip = CompositeVideoClip([final_clip, txt])
        print("  📝  Poem text overlay added at the end")
    except Exception as e:
        print(f"  ⚠️  Text overlay skipped: {e}")

    # ── Export ──────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"  💾  Exporting final video (this may take a few minutes)…")
    try:
        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="slow",
            bitrate="5000k",
            threads=4,
            logger="bar",
        )
    finally:
        for c in clips:
            c.close()
        try:
            final_clip.close()
        except Exception:
            pass

    print(f"\n  🎉  Video saved → {output_path}")
    return True


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print_banner(
        "MOON & SUN POETIC VIDEO GENERATOR\n"
        "Using Google Veo 2 API  +  moviepy\n"
        "Estimated total time: 20-40 minutes"
    )

    # ── Import google-genai ─────────────────────────────────────────
    try:
        from google import genai
    except ImportError:
        print("❌  google-genai not installed. Run:\n    pip install google-genai")
        sys.exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌  No API key found. Set GOOGLE_API_KEY in your environment or .env file.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print(f"✅  Veo client initialized (model: {VEO_MODEL})\n")

    # ── Check pictures ──────────────────────────────────────────────
    missing = [p for p in PORTRAIT_PHOTOS if not (PICTURES_DIR / p).exists()]
    if missing:
        print(f"⚠️  Some reference photos not found (will skip image-to-video for those):")
        for m in missing:
            print(f"   • {m}")
        print()

    progress = load_progress()

    # ── MOON VIDEO ──────────────────────────────────────────────────
    print_banner("GENERATING MOON VIDEO\n" + MOON_POEM, "─")
    moon_clips = generate_all_clips(client, MOON_SCENES, "moon", progress)

    if moon_clips:
        stitch_video(
            clip_paths=moon_clips,
            output_path=OUTPUT_DIR / "moon_video.mp4",
            poem_text=MOON_POEM,
            song_path=SONG_PATH,
        )
    else:
        print("⚠️  No moon clips generated — skipping moon video stitching")

    # ── SUN VIDEO (Commented out for refined Moon-only run) ───────────
    # print_banner("GENERATING SUN VIDEO\n" + SUN_POEM, "─")
    # sun_clips = generate_all_clips(client, SUN_SCENES, "sun", progress)
    # 
    # if sun_clips:
    #     stitch_video(
    #         clip_paths=sun_clips,
    #         output_path=OUTPUT_DIR / "sun_video.mp4",
    #         poem_text=SUN_POEM,
    #         song_path=SONG_PATH,
    #     )
    # else:
    #     print("⚠️  No sun clips generated — skipping sun video stitching")

    # ── Done ────────────────────────────────────────────────────────
    print_banner(
        "ALL DONE!\n\n"
        "Your videos are in:  adventure_backend/generated_videos/\n"
        "  • moon_video.mp4\n"
        "  • sun_video.mp4\n\n"
        "Copy them to:  adventure_frontend/public/videos/\n"
        "and reference as:  /videos/moon_video.mp4"
    )


if __name__ == "__main__":
    # Load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    main()
