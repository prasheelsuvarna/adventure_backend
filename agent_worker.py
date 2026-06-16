import asyncio
import json
import logging
import os
import sys

if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from livekit.agents import AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli, room_io, JobExecutorType
from livekit.agents.voice import Agent
from livekit.plugins import google, noise_cancellation
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY,
    GEMINI_REALTIME_MODEL,
    GEMINI_VOICE,
    LIVEKIT_AGENT_NAME,
    SYSTEM_PROMPT,
)

load_dotenv()

# Prioritize our local GEMINI_API_KEY and synchronize env vars
local_gemini = os.getenv("GEMINI_API_KEY")
if local_gemini:
    os.environ["GOOGLE_API_KEY"] = local_gemini
    os.environ["GEMINI_API_KEY"] = local_gemini


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("birthday-agent")

# Initialize Gemini Client for transcript translations
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("GenAI client initialized successfully in agent worker.")
    except Exception as e:
        logger.error(f"Failed to initialize GenAI client in worker: {e}")



class BirthdayVoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model=GEMINI_REALTIME_MODEL,
            voice=GEMINI_VOICE,
            temperature=0.8,
        ),
    )

    agent = BirthdayVoiceAgent()

    # Listen to data packets from the room (user chat / events)
    @ctx.room.on("data_received")
    def on_data_received(data_packet):
        try:
            payload = json.loads(data_packet.data.decode("utf-8"))
            msg_type = payload.get("type")
            
            if getattr(session._llm, "_sessions", None) and list(session._llm._sessions):
                realtime_session = list(session._llm._sessions)[0]
                if getattr(realtime_session, "_active_session", None):
                    if msg_type == "chat":
                        text = payload.get("text", "")
                        if text:
                            logger.info("Received user chat text: %s", text)
                            realtime_session._send_client_event(
                                types.LiveClientRealtimeInput(text=text)
                            )
                            logger.info("Successfully injected text input to Gemini session")
                    elif msg_type == "gift_opened":
                        logger.info("Received gift_opened trigger. Directing Aria to respond in Kanglish.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to say warmly in conversational Kanglish (Kannada mixed naturally with English) "
                                    "that she can definitely zoom in to see the portrait, ask if it looks great, "
                                    "and suggest continuing the adventure by clicking the button to go to the next screen. "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "quiz_started":
                        question = payload.get("question", "")
                        logger.info(f"Received quiz_started trigger. Directing Aria to explain and read question: {question}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to explain to Manohari in conversational Kanglish (Kannada mixed naturally with English) "
                                    "what the quiz is about: based on her choices in this personality quiz, she will get a special surprise portrait at the end. "
                                    "Then, direct her to read out the first question: 'Which landscape vibes with your soul the most?' "
                                    "and ask her: 'Which might you choose?' (Which one might you choose?). "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "quiz_question":
                        question = payload.get("question", "")
                        index = payload.get("index", 1)
                        logger.info(f"Received quiz_question trigger. Directing Aria to read question {index}: {question}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to read out the next question in conversational Kanglish (Kannada mixed naturally with English): "
                                    f"Say index '{index}ನೇ ಪ್ರಶ್ನೆ' (e.g., 'Question 2' or 'Question 3'), read the question text '{question}', "
                                    "and ask which one she might choose. "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "quiz_option_selected":
                        option = payload.get("option", "")
                        logger.info(f"Received quiz_option_selected trigger. Directing Aria to compliment option: {option}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    f"Direct Aria to give a natural compliment in conversational Kanglish (Kannada mixed naturally with English) for choosing option '{option}'. "
                                    "After the compliment, she must tell Manohari to click the next question button to continue, saying exactly: 'Next question click madi, munduvarasi' (ನೆಕ್ಸ್ಟ್ ಕ್ವೆಶ್ಚನ್ ಕ್ಲಿಕ್ ಮಾಡಿ, ಮುಂದುವರಸಿ). "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "quiz_completed":
                        logger.info("Received quiz_completed trigger. Directing Aria to respond with surprise message.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English) "
                                    "that she has seen all of Manohari's favorites and they are wonderful. "
                                    "Then say that she has prepared a special surprise for her, and ask if she would like to see it. "
                                    "Tell her to click the button below to open the surprise. "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "portrait_shown":
                        logger.info("Received portrait_shown trigger. Directing Aria to ask for feedback.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask in conversational Kanglish (Kannada mixed naturally with English): "
                                    "how the portrait is, and if it looks good. Ask her to please click either 'howdu' (yes) or 'illa' (no) "
                                    "on the screen to let us know. E.g. 'Hegide portrait? Chennagide alva? Dayavittu howdu or illa click madi namge tilisi.' "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "portrait_feedback":
                        choice = payload.get("choice", "")
                        logger.info(f"Received portrait_feedback trigger with choice: {choice}")
                        if choice == "howdu":
                            feedback_instruction = (
                                "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English): "
                                "thank you so much, and that she is so glad and happy that Manohari liked the portrait! "
                                "E.g. 'Thank you! Nimge ishta aagiddu nodi nange tumba khushi aaytu!' "
                                "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                            )
                        else:
                            feedback_instruction = (
                                "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English): "
                                "oh is that so? That's alright, next time she will try to make it even more beautiful. "
                                "E.g. 'Ohh howda, next time innu chennagi madlikke try madtini.' "
                                "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                            )
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(text=feedback_instruction)
                        )
                    elif msg_type == "quiz2_started":
                        logger.info("Received quiz2_started trigger. Directing Aria to introduce Quiz 2 in Kanglish.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to explain to Manohari in conversational Kanglish (Kannada mixed naturally with English) "
                                    "that this second quiz is just like the previous one: answer 3 questions, and see another custom portrait based on her choices. "
                                    "She must say exactly in Kannada/Kanglish: 'Idu sa same hindina tara 3 question ans madi ans madida parakara nimma potrait nodi' "
                                    "(ಇದು ಸಹ ಸೇಮ್ ಹಿಂದಿನ ತರ 3 ಕ್ವೆಶ್ಚನ್ ಆನ್ಸರ್ ಮಾಡಿ, ಆನ್ಸರ್ ಮಾಡಿದ ಪ್ರಕಾರ ನಿಮ್ಮ ಪೋರ್ಟ್ರೇಟ್ ನೋಡಿ). "
                                    "Then, direct her to read Question 1 of the second quiz: 'Which dreamy backdrop matches your aura?' "
                                    "and ask her which option she might choose. "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "quiz2_completed":
                        logger.info("Received quiz2_completed trigger. Directing Aria to respond with second surprise portrait message.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English) "
                                    "that she has prepared a second, beautiful surprise portrait for Manohari! "
                                    "Tell her to click the button below to open the second surprise. "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "portrait_shown_2":
                        logger.info("Received portrait_shown_2 trigger. Directing Aria to ask for feedback on the second portrait.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask in conversational Kanglish (Kannada mixed naturally with English): "
                                    "how this second portrait is, and if it looks good. Ask her to please click either 'howdu' (yes) or 'illa' (no) "
                                    "on the screen to let us know. E.g. 'Hegide second portrait? Chennagide alva? Dayavittu howdu or illa click madi namge tilisi.' "
                                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                                )
                            )
                        )
                    elif msg_type == "portrait_feedback_2":
                        choice = payload.get("choice", "")
                        logger.info(f"Received portrait_feedback_2 trigger with choice: {choice}")
                        if choice == "howdu":
                            feedback_instruction = (
                                "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English): "
                                "thank you so much, and that she is so happy that Manohari liked the second portrait! "
                                "E.g. 'Thank you! Nimge ishta aagiddu nodi nange tumba khushi aaytu!' "
                                "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                            )
                        else:
                            feedback_instruction = (
                                "Direct Aria to say in conversational Kanglish (Kannada mixed naturally with English): "
                                "oh is that so? That's alright, she will try to make it even more beautiful next time. "
                                "E.g. 'Ohh howda, next time innu chennagi madlikke try madtini.' "
                                "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                            )
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(text=feedback_instruction)
                        )
                    elif msg_type == "poetry_started":
                        logger.info("Received poetry_started trigger. Directing Aria to explain.")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to say warmly, softly, and politely in conversational Kanglish (Kannada mixed naturally with English) "
                                    "that her creator has written some beautiful and heartfelt poetry lines especially for her. "
                                    "Tell her with gentle, warm emotion that she should click the button to unlock the first line. "
                                    "Speak like a normal, warm, and friendly human. Do NOT be dramatic or exaggerated, but show polite, gentle warmth."
                                )
                            )
                        )
                    elif msg_type == "poetry_unlocked":
                        index = payload.get("index", 1)
                        logger.info(f"Received poetry_unlocked trigger for line index: {index}")
                        if index == 1:
                            line_text = "In a sky full of stars, you are the only moon I notice."
                        elif index == 2:
                            line_text = "If you were the sun I would continue to stare at you. Even if it costs my vision for i would know the last thing I saw was perfection."
                        else:
                            line_text = "I wish I was your tear, so I could be born in your eye, run down your cheek, and die upon your lips."
                        
                        text_instruction = (
                            f"Direct Aria to read out this poetry line with deep warmth, soft feeling, and gentle, polite poetic emotion: '{line_text}'. "
                            "Speak the line slowly, softly, and beautifully. After reading this specific line, transition back to her normal friendly tone "
                            "and ask Manohari to rate the poetry line from 1 to 5 stars on the screen (using conversational Kanglish, Kannada mixed naturally with English). "
                            "Do NOT mention any video, video surprise, or video buttons. "
                            "Maintain a natural, warm human voice, avoiding exaggerated or fake dramatic tones, but make the line reading itself feel touching and gentle."
                        )
                        
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(text=text_instruction)
                        )
                    elif msg_type == "poetry_page_changed":
                        logger.info("Received poetry_page_changed trigger. Interrupted speech to remain quiet.")
                        try:
                            session.interrupt(force=True)
                        except Exception as e:
                            logger.warning(f"Failed to interrupt agent speech: {e}")
                    elif msg_type == "convo_q1":
                        logger.info("convo_q1: Aria to ask Q1 (site liked?)")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask Manohari warmly in conversational Kanglish: "
                                    "'Are you liking this site we built for you? (Nimge ee site ishta aagidya?) "
                                    "You can click Howdu or Illa on the screen, or just speak!' "
                                    "Keep it light, warm and friendly. Don't be dramatic."
                                )
                            )
                        )
                    elif msg_type == "convo_q1_answered":
                        answer = payload.get("answer", "")
                        logger.info(f"convo_q1_answered: {answer}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    f"Direct Aria to react naturally in conversational Kanglish to her answer: '{answer}'. "
                                    "Keep it short, warm, 1-2 sentences. "
                                    "Do NOT ask any new question, just react and encourage her."
                                )
                            )
                        )
                    elif msg_type == "convo_q2":
                        logger.info("convo_q2: Aria to ask birthday plans")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask Manohari in conversational Kanglish: "
                                    "'Yenu special madtidira bday dina? What are your plans for your birthday? "
                                    "You can type or just tell me!' "
                                    "Keep it casual and excited like talking to a close friend."
                                )
                            )
                        )
                    elif msg_type == "convo_q2_answered":
                        answer = payload.get("answer", "")
                        logger.info(f"convo_q2_answered: {answer}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    f"Direct Aria to warmly react to her birthday plans: '{answer}'. "
                                    "Give a genuine, happy compliment on her plans in conversational Kanglish. "
                                    "Keep it 1-2 sentences, warm, and don't ask anything new."
                                )
                            )
                        )
                    elif msg_type == "convo_q3":
                        logger.info("convo_q3: Aria to ask for message to creator")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask Manohari in conversational Kanglish: "
                                    "'Is there any message you'd like to leave for my creator? "
                                    "I'll make sure it reaches him directly. You can type or speak it!' "
                                    "Keep the tone sweet, gentle, and heartfelt."
                                )
                            )
                        )
                    elif msg_type == "convo_q3_answered":
                        answer = payload.get("answer", "")
                        logger.info(f"convo_q3_answered (message for creator): {answer}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    f"Direct Aria to warmly acknowledge and confirm her message for the creator: '{answer}'. "
                                    "Tell her in conversational Kanglish that the message will definitely be delivered and it means a lot. "
                                    "Keep it short, 1-2 sentences, and very heartfelt."
                                )
                            )
                        )
                    elif msg_type == "convo_q4":
                        logger.info("convo_q4: Aria to ask about celebrating together next birthday")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    "Direct Aria to ask Manohari in conversational Kanglish: "
                                    "'Is there any possibility that next year on your birthday, "
                                    "you will be able to celebrate with my creator again? "
                                    "Howdu or Illa? You can click the button or just tell me!' "
                                    "Ask gently, warmly, with no pressure at all."
                                )
                            )
                        )
                    elif msg_type == "convo_q4_answered":
                        answer = payload.get("answer", "")
                        logger.info(f"convo_q4_answered: {answer}")
                        realtime_session._send_client_event(
                            types.LiveClientRealtimeInput(
                                text=(
                                    f"Direct Aria to warmly close the conversation in conversational Kanglish based on her answer: '{answer}'. "
                                    "If she said yes/howdu, celebrate that warmly. "
                                    "If she said no/illa, be very gracious and say that's perfectly okay, she is always special. "
                                    "Wrap up by wishing her a wonderful birthday and tell her there's one last surprise waiting "
                                    "— she can click the button to continue. Keep it warm and genuine."
                                )
                            )
                        )

        except Exception as e:
            logger.error("Error in on_data_received: %s", e)

    # Listen to agent speech to send transcripts back to client
    @session.on("agent_speech_committed")
    def on_agent_speech_committed(msg):
        text = getattr(msg, "content", "") or getattr(msg, "text", "") or str(msg)
        if text.strip() and ctx.room and ctx.room.isconnected():
            display_text = text.strip()
            
            # Dictionary matching for predefined lines to avoid API calls / lag
            predefined = {
                "ಖಂಡಿತವಾಗಿಯೂ ನೀವು ಅದನ್ನ zoom ಮಾಡಿ ನೋಡಬಹುದು": "Of course you can zoom in and see it! It looks great, doesn't it? Let's continue our adventure, click the button to go to the next screen.",
                "ನಿಮ್ಮ favorites ಎಲ್ಲವನ್ನೂ ನೋಡಿದೆ": "I saw all your favorites, they are so nice! According to them, I have a surprise for you. Would you like to see it? Click the button below.",
                "ಬನ್ನಿ ನಮ್ಮ adventure ನ ಸ್ಟಾರ್ಟ್ ಮಾಡೋಣ": "Happy Birthday Manohari! Let's start our adventure. Before that, a welcome gift awaits you. Click the gift box to open it.",
                "surprises, personality games": "A birthday adventure awaits you! 🎂",
                "welcome gift": "Happy Birthday Manohari! Let's start our adventure. Before that, a welcome gift awaits you. Click the gift box to open it.",
                "Personality Quiz": "In this personality quiz, you'll get a special surprise based on your choices! First question: Which landscape vibes with your soul the most? Which one might you choose?",
                "Next question click": "Awesome! Click Next Question to continue.",
                "ಮುಂದುವರಸಿ": "Awesome! Click Next Question to continue.",
                "Hegide portrait": "How is the portrait? Good, right? Please click yes or no and let us know.",
                "ishta aagiddu nodi": "Thank you! I am so glad you liked it!",
                "innu chennagi madlikke": "Oh, is that so? Next time I will try to make it even better."
            }
            
            matched = False
            for k, v in predefined.items():
                if k in display_text:
                    display_text = v
                    matched = True
                    break
            
            # If not predefined, translate dynamically via Gemini GenAI client
            if not matched and gemini_client:
                try:
                    translation_resp = gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Translate this Kannada/Kanglish text to natural, friendly English. Return only the English translation: {display_text}"
                    )
                    display_text = translation_resp.text.strip()
                    logger.info(f"Translated agent speech from '{text.strip()}' to '{display_text}'")
                except Exception as e:
                    logger.error(f"Failed to translate agent speech: {e}")

            payload = json.dumps({
                "type": "agent_chat",
                "text": display_text
            }).encode("utf-8")
            
            async def send():
                try:
                    await ctx.room.local_participant.publish_data(payload)
                except Exception as err:
                    logger.error("Failed to publish agent transcript: %s", err)
            
            asyncio.create_task(send())

    # Listen to user speech to send transcripts back to client
    @session.on("user_speech_committed")
    def on_user_speech_committed(msg):
        text = getattr(msg, "content", "") or getattr(msg, "text", "") or str(msg)
        if text.strip() and ctx.room and ctx.room.isconnected():
            payload = json.dumps({
                "type": "user_chat",
                "text": text.strip()
            }).encode("utf-8")
            
            async def send():
                try:
                    await ctx.room.local_participant.publish_data(payload)
                except Exception as err:
                    logger.error("Failed to publish user transcript: %s", err)
            
            asyncio.create_task(send())

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        ),
    )

    # Greet Manohari immediately when connecting (in Kanglish)
    async def greet():
        # Parse stage from metadata
        stage = "intro"
        if ctx.job and ctx.job.metadata:
            try:
                meta = json.loads(ctx.job.metadata)
                stage = meta.get("stage", "intro")
            except Exception as e:
                logger.warning(f"Failed to parse job metadata: {e}")
        
        logger.info(f"Greeting participant. Current stage: {stage}")
        
        # Wait for the realtime session to become active (up to 10 seconds)
        realtime_session = None
        for _ in range(50):  # 50 * 0.2s = 10s
            await asyncio.sleep(0.2)
            if getattr(session._llm, "_sessions", None) and list(session._llm._sessions):
                temp_session = list(session._llm._sessions)[0]
                if getattr(temp_session, "_active_session", None):
                    realtime_session = temp_session
                    break
        
        if realtime_session:
            if stage == "quiz":
                greeting_text = (
                    "Direct Aria to explain to Manohari in conversational Kanglish (Kannada mixed naturally with English) "
                    "what the quiz is about: based on her choices in this personality quiz, she will get a special surprise portrait at the end. "
                    "Then, direct her to read out the first question: 'Which landscape vibes with your soul the most?' "
                    "and ask her which one she might choose. "
                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                )
            elif stage == "wyr":
                greeting_text = (
                    "Direct Aria to say warmly, softly, and politely in conversational Kanglish (Kannada mixed naturally with English) "
                    "that her creator has written some beautiful and heartfelt poetry lines especially for her, and she "
                    "should click the button to unlock the first line. "
                    "Speak like a normal, warm, friendly human, avoiding exaggerated dramatic phrases, but expressing gentle and polite emotion."
                )
            elif stage == "conversation":
                greeting_text = (
                    "Direct Aria to greet Manohari warmly in conversational Kanglish (Kannada mixed naturally with English). "
                    "Say Happy Birthday and welcome her to the special chat room. "
                    "Tell her she can type or speak, and that Aria is here to chat with her. "
                    "Keep it short, warm, and casual like greeting a close friend. "
                    "Do NOT ask any questions yet — just warmly welcome her."
                )
            else:
                greeting_text = (
                    "Greet Manohari in conversational Kanglish (Kannada mixed naturally with English). "
                    "Wish her a happy birthday and tell her: 'Happy Birthday Manohari! Let's start our adventure. "
                    "Before that, a welcome gift is waiting for you, click the gift box to open it.' "
                    "Speak like a normal, calm, friendly human. Do NOT be dramatic or exaggerated."
                )
            
            if greeting_text:
                realtime_session._send_client_event(
                    types.LiveClientRealtimeInput(text=greeting_text)
                )
                logger.info("Sent initial stage-based greeting instruction to agent")
            else:
                logger.info("No greeting configured for this stage, staying silent.")
        else:
            logger.error("Could not send initial stage-based greeting: Realtime session did not become active in time.")

    asyncio.create_task(greet())

    disconnected = asyncio.Event()
    ctx.room.on("participant_disconnected", lambda *_: disconnected.set())
    ctx.room.on("disconnected", lambda *_: disconnected.set())

    await disconnected.wait()
    await session.aclose()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=LIVEKIT_AGENT_NAME,
            job_executor_type=JobExecutorType.THREAD,
        )
    )
