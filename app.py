"""
MindQuiet Backend — FastAPI
5-Stage Mental Wellness Game
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import random
import datetime

app = FastAPI(title="MindQuiet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# IN-MEMORY STORE  (swap for a real DB in prod)
# ─────────────────────────────────────────────
sessions: dict = {}   # session_id → PlayerSession


# ─────────────────────────────────────────────
# GAME DATA
# ─────────────────────────────────────────────

MOOD_CONFIG = {
    "angry": {
        "theme_color": "#4A90D9",
        "theme_name": "Soft Blue",
        "goal": "Calm the nervous system and reduce intensity.",
        "music_type": "Soft piano",
        "tempo_bpm": "60–70 BPM",
        "plant_stage": 1,
        "stage2_puzzle": "smash",
        "seed_message": "Every journey begins with a small seed. Planting in anger — you're already taking control. 🌰",
    },
    "sad": {
        "theme_color": "#F6C90E",
        "theme_name": "Sunny Yellow",
        "goal": "Increase positivity and energy.",
        "music_type": "Acoustic guitar",
        "tempo_bpm": "80–100 BPM",
        "plant_stage": 1,
        "stage2_puzzle": "color_match",
        "seed_message": "Even in rain, seeds know how to grow. Your journey starts now. 🌰",
    },
    "anxious": {
        "theme_color": "#B39DDB",
        "theme_name": "Lavender",
        "goal": "Slow the mind and breathing.",
        "music_type": "Binaural beats (Alpha waves) + Slow ambient",
        "tempo_bpm": "50–60 BPM",
        "plant_stage": 1,
        "stage2_puzzle": "breathing_rhythm",
        "seed_message": "Breathe in. Breathe out. You are safe. Your seed is planted. 🌰",
    },
    "tired": {
        "theme_color": "#FF9800",
        "theme_name": "Warm Orange",
        "goal": "Wake the brain gently.",
        "music_type": "Soft energetic lo-fi",
        "tempo_bpm": "100–120 BPM",
        "plant_stage": 1,
        "stage2_puzzle": "quick_reaction",
        "seed_message": "Rest is growth too. But today, let's gently wake up together. 🌰",
    },
}

STAGE_PLANT_MESSAGES = {
    1: ("🌰 Seed", "Recognizing your emotions is the first step to growth."),
    2: ("🌱 Sapling", "Calming your mind helps new growth begin."),
    3: ("🌿 Baby Plant", "Confidence grows when you practice."),
    4: ("🌳 Growing Plant", "Focus gives strength to your growth."),
    5: ("🌹 Flower / 🍎 Fruit", "You bloomed. Growth happens one small step at a time."),
}

CONVERSATION_SCENARIOS = [
    {
        "id": 1,
        "title": "Giving a Compliment",
        "prompt": "Imagine your friend did a great presentation. What would you say?",
        "examples": ["You explained that really well.", "Your presentation was very clear."],
        "feedback": "Nice! Compliments make people feel appreciated.",
    },
    {
        "id": 2,
        "title": "Introducing Yourself",
        "prompt": "Let's practice introducing yourself to someone new.",
        "examples": ["Hi, I'm Mia. I like drawing and photography."],
        "feedback": "Great! Saying your name clearly helps people remember you.",
    },
    {
        "id": 3,
        "title": "Asking for Directions",
        "prompt": "Imagine you are in a new place and need directions. What would you say?",
        "examples": ["Excuse me, could you tell me where the library is?"],
        "feedback": "Very polite. Good job asking clearly.",
    },
    {
        "id": 4,
        "title": "Joining a Group Conversation",
        "prompt": "Some classmates are talking about a movie you watched. How would you join?",
        "examples": ["I watched that movie too! It was really good."],
        "feedback": "Nice! Adding your opinion helps you join the group.",
    },
    {
        "id": 5,
        "title": "Asking for Help",
        "prompt": "You didn't understand a homework question. What would you say to your teacher?",
        "examples": ["Excuse me, could you explain this question again?"],
        "feedback": "Good! Asking for help is a strong skill.",
    },
    {
        "id": 6,
        "title": "Saying No Politely",
        "prompt": "Your friend asks you to skip class. What would you say?",
        "examples": ["I can't today, I have an important class."],
        "feedback": "Great! You said no in a respectful way.",
    },
]

AFFIRMATIONS = [
    "Growth happens one small step at a time. 🌱",
    "You are stronger than you think. 💪",
    "Every breath is a new beginning. 🌬️",
    "Your mind is calmer than it was yesterday. 🌿",
    "You showed up for yourself today — that matters. ✨",
    "Peace is not something you find. It's something you grow. 🌸",
    "Small progress is still progress. Keep going. 🍎",
    "You are capable of amazing things. 🌟",
]

BADGES = {
    "calm_mind":    {"emoji": "🌿", "name": "Calm Mind",     "description": "Completed a calming puzzle"},
    "brave_speaker":{"emoji": "🗣",  "name": "Brave Speaker", "description": "Practiced conversations"},
    "focus_master": {"emoji": "🎯", "name": "Focus Master",  "description": "Finished attention games"},
    "growth_star":  {"emoji": "✨", "name": "Growth Star",   "description": "Completed all 5 stages"},
}


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    player_name: Optional[str] = "Friend"

class MoodRequest(BaseModel):
    session_id: str
    mood: str  # angry | sad | anxious | tired

class StageCompleteRequest(BaseModel):
    session_id: str
    stage: int
    score: Optional[int] = 0

class SpeechFeedbackRequest(BaseModel):
    session_id: str
    scenario_id: int
    player_response: str  # transcribed text from mic

class PlayerSession(BaseModel):
    session_id: str
    player_name: str
    mood: Optional[str] = None
    current_stage: int = 0
    plant_stage: int = 0
    badges: list = []
    streak_days: int = 1
    stages_completed: list = []
    started_at: str = ""
    score_total: int = 0


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_session(session_id: str) -> PlayerSession:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new session.")
    return sessions[session_id]

def generate_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8].upper()

def evaluate_speech(player_response: str, scenario: dict) -> dict:
    """
    Simple keyword-based speech evaluation.
    In production, replace with an NLP / LLM call.
    """
    response_lower = player_response.lower().strip()
    positive_words = ["please", "excuse", "thank", "sorry", "could", "would", "great", "nice", "good"]
    confidence_words = ["i", "my", "me", "i'm", "i'd", "i've"]
    clarity_score = sum(1 for w in positive_words if w in response_lower)
    confidence_score = sum(1 for w in confidence_words if w in response_lower)

    if len(response_lower) < 5:
        tone = "Try speaking a little more. You've got this! 😊"
    elif clarity_score >= 2:
        tone = "That sounded confident and polite! 🌟"
    elif confidence_score >= 1:
        tone = "Good start! Try speaking a little louder and slower. 💬"
    else:
        tone = "Nice effort! Remember to breathe and take your time. 🌿"

    return {
        "feedback": scenario["feedback"],
        "tone": tone,
        "pre_response_message": "Take a deep breath… speak slowly… you've got this. 🌬️",
    }


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "🌱 MindQuiet API is running.", "version": "1.0.0"}


# ── SESSION ──────────────────────────────────

@app.post("/session/start")
def start_session(req: StartSessionRequest):
    """Create a new player session."""
    sid = generate_id()
    session = PlayerSession(
        session_id=sid,
        player_name=req.player_name,
        started_at=datetime.datetime.utcnow().isoformat(),
    )
    sessions[sid] = session
    return {
        "session_id": sid,
        "player_name": req.player_name,
        "message": f"Welcome, {req.player_name}! 🌱 Let's begin your journey.",
    }

@app.get("/session/{session_id}")
def get_session_info(session_id: str):
    """Get current session state."""
    s = get_session(session_id)
    return s


# ── STAGE 1 — MOOD SELECTION ─────────────────

@app.post("/stage1/mood")
def set_mood(req: MoodRequest):
    """
    Player selects their mood.
    Returns theme, music config, and plants the seed.
    """
    mood = req.mood.lower()
    if mood not in MOOD_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid mood. Choose from: {list(MOOD_CONFIG.keys())}")

    s = get_session(req.session_id)
    s.mood = mood
    s.current_stage = 1
    s.plant_stage = 1

    config = MOOD_CONFIG[mood]
    plant_label, plant_msg = STAGE_PLANT_MESSAGES[1]

    return {
        "stage": 1,
        "mood": mood,
        "theme_color": config["theme_color"],
        "theme_name": config["theme_name"],
        "goal": config["goal"],
        "music_type": config["music_type"],
        "tempo_bpm": config["tempo_bpm"],
        "stage2_puzzle": config["stage2_puzzle"],
        "plant": {
            "stage": plant_label,
            "message": plant_msg,
            "seed_message": config["seed_message"],
        },
        "character_dialogue": f"Hello {s.player_name}! I can see you're feeling {mood} today. That's okay — let's work through it together. 🌱",
    }


# ── STAGE 2 — PUZZLE GAME ─────────────────────

@app.get("/stage2/puzzle/{session_id}")
def get_puzzle(session_id: str):
    """Return the puzzle config based on the player's mood."""
    s = get_session(session_id)
    if not s.mood:
        raise HTTPException(status_code=400, detail="Mood not set. Complete Stage 1 first.")

    puzzle_type = MOOD_CONFIG[s.mood]["stage2_puzzle"]

    puzzle_map = {
        "smash": {
            "type": "smash",
            "title": "Release the Tension 💥",
            "instruction": "Tap the blocks to gently crush them. Let the tension melt away.",
            "total_blocks": 12,
            "time_limit_seconds": 45,
            "success_message": "You released the tension. Feel your breath slow down. 🌬️",
        },
        "color_match": {
            "type": "color_match",
            "title": "Color Burst 🌈",
            "instruction": "Match 3–4 colors. Each match brightens your world!",
            "grid_size": 6,
            "colors": ["#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#FF9F45", "#C77DFF"],
            "matches_needed": 10,
            "success_message": "Beautifully done! Feel the brightness spreading. ☀️",
        },
        "breathing_rhythm": {
            "type": "breathing_rhythm",
            "title": "Breathe With Me 🫧",
            "instruction": "Tap when the circle is fully expanded (inhale), tap again when fully shrunk (exhale).",
            "inhale_seconds": 4,
            "exhale_seconds": 6,
            "rounds": 6,
            "success_message": "Your breathing is slower. Your mind is quieter. 🌊",
        },
        "quick_reaction": {
            "type": "quick_reaction",
            "title": "Shape Blink ⚡",
            "instruction": "Shapes will flash briefly. Choose the matching pattern before it disappears!",
            "display_time_ms": 800,
            "rounds": 10,
            "shapes": ["circle", "triangle", "square", "star", "hexagon"],
            "success_message": "Your brain is waking up! Nice reflexes. 🌟",
        },
    }

    return {
        "stage": 2,
        "mood": s.mood,
        "puzzle": puzzle_map[puzzle_type],
        "character_dialogue": "Let's play a little game. It will help your mind find peace. Ready? 🎮",
    }

@app.post("/stage2/complete")
def complete_stage2(req: StageCompleteRequest):
    """Mark Stage 2 complete, grow plant to sapling."""
    s = get_session(req.session_id)
    s.current_stage = 2
    s.plant_stage = 2
    s.score_total += req.score
    if 2 not in s.stages_completed:
        s.stages_completed.append(2)
        s.badges.append("calm_mind")

    plant_label, plant_msg = STAGE_PLANT_MESSAGES[2]
    return {
        "stage": 2,
        "status": "complete",
        "badge_earned": BADGES["calm_mind"],
        "plant": {"stage": plant_label, "message": plant_msg},
        "character_dialogue": "Wonderful! Look — your seed has sprouted! 🌱 Your mind is already calmer.",
    }


# ── STAGE 3 — SOCIAL CONFIDENCE ──────────────

@app.get("/stage3/scenarios")
def get_scenarios():
    """Return all 6 conversation scenarios."""
    return {
        "stage": 3,
        "title": "Social Confidence Practice 🗣",
        "character_intro": "Let's practice some real-life conversations. Don't worry if you make mistakes. Just take a deep breath and speak slowly.",
        "pre_response_reminder": "Take a deep breath… speak slowly… you've got this. 🌬️",
        "scenarios": CONVERSATION_SCENARIOS,
    }

@app.post("/stage3/evaluate")
def evaluate_response(req: SpeechFeedbackRequest):
    """Evaluate a player's spoken response for a scenario."""
    scenario = next((s for s in CONVERSATION_SCENARIOS if s["id"] == req.scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    result = evaluate_speech(req.player_response, scenario)
    return {
        "stage": 3,
        "scenario_id": req.scenario_id,
        "scenario_title": scenario["title"],
        "player_response": req.player_response,
        **result,
    }

@app.post("/stage3/complete")
def complete_stage3(req: StageCompleteRequest):
    """Mark Stage 3 complete, grow plant."""
    s = get_session(req.session_id)
    s.current_stage = 3
    s.plant_stage = 3
    s.score_total += req.score
    if 3 not in s.stages_completed:
        s.stages_completed.append(3)
        s.badges.append("brave_speaker")

    plant_label, plant_msg = STAGE_PLANT_MESSAGES[3]
    return {
        "stage": 3,
        "status": "complete",
        "badge_earned": BADGES["brave_speaker"],
        "plant": {"stage": plant_label, "message": plant_msg},
        "character_dialogue": "Look at your plant! More leaves, stronger stem. 🌿 You're growing, just like it.",
    }


# ── STAGE 4 — FOCUS & ATTENTION ──────────────

@app.get("/stage4/games")
def get_focus_games():
    """Return focus game configs."""
    return {
        "stage": 4,
        "title": "Focus & Attention Training 🎯",
        "character_intro": "Let's train your focus. Stay calm and pay attention to the details.",
        "games": [
            {
                "id": "firefly",
                "title": "Firefly Focus 🌙",
                "goal": "Improve selective attention.",
                "instructions": "Tap only the BLUE glowing fireflies. Ignore yellow and red ones.",
                "target_color": "blue",
                "distractor_colors": ["yellow", "red"],
                "total_fireflies": 20,
                "time_limit_seconds": 30,
                "wrong_tap_message": "Focus on the blue ones. 💙",
                "environment": {
                    "background": "dark_night_forest",
                    "music": "calm_ambient",
                    "effects": "soft_glowing_lights",
                },
            },
            {
                "id": "falling_leaves",
                "title": "Falling Leaves 🍃",
                "goal": "Improve visual focus and decision making.",
                "instructions": "Catch only the GREEN leaves. Let red, yellow, and brown ones fall.",
                "target_color": "green",
                "distractor_colors": ["red", "yellow", "brown"],
                "total_leaves": 25,
                "fall_speed_seconds": 3,
                "environment": {
                    "background": "soft_forest",
                    "music": "relaxing_wind",
                    "effects": "gentle_breeze",
                },
            },
        ],
    }

@app.post("/stage4/complete")
def complete_stage4(req: StageCompleteRequest):
    """Mark Stage 4 complete, grow plant into tree."""
    s = get_session(req.session_id)
    s.current_stage = 4
    s.plant_stage = 4
    s.score_total += req.score
    if 4 not in s.stages_completed:
        s.stages_completed.append(4)
        s.badges.append("focus_master")

    plant_label, plant_msg = STAGE_PLANT_MESSAGES[4]
    return {
        "stage": 4,
        "status": "complete",
        "badge_earned": BADGES["focus_master"],
        "plant": {"stage": plant_label, "message": plant_msg},
        "character_dialogue": "Your plant is tall and strong now! 🌳 Just like your focused mind.",
    }


# ── STAGE 5 — REWARDS & AFFIRMATIONS ─────────

@app.post("/stage5/complete")
def complete_stage5(req: StageCompleteRequest):
    """Final stage — bloom the plant, award badges, reveal affirmation."""
    s = get_session(req.session_id)
    s.current_stage = 5
    s.plant_stage = 5
    s.score_total += req.score
    if 5 not in s.stages_completed:
        s.stages_completed.append(5)

    # Award Growth Star if all stages done
    all_done = all(i in s.stages_completed for i in [1, 2, 3, 4, 5])
    if all_done and "growth_star" not in s.badges:
        s.badges.append("growth_star")

    # Pick a random affirmation
    affirmation = random.choice(AFFIRMATIONS)
    plant_label, plant_msg = STAGE_PLANT_MESSAGES[5]

    earned_badges = [BADGES[b] for b in s.badges if b in BADGES]

    return {
        "stage": 5,
        "status": "complete",
        "plant": {
            "stage": plant_label,
            "message": plant_msg,
            "bloom_type": "apple_tree" if s.mood in ["tired", "angry"] else "flower",
            "affirmation": affirmation,
        },
        "badges_earned": earned_badges,
        "streak_days": s.streak_days,
        "total_score": s.score_total,
        "character_dialogue": f"Great work today, {s.player_name}! Let's see what you achieved. 🌟",
        "streak_message": "You completed today's session. Come back tomorrow to continue your growth. 🌱",
        "all_stages_complete": all_done,
    }


# ── PROGRESS ─────────────────────────────────

@app.get("/progress/{session_id}")
def get_progress(session_id: str):
    """Get full player progress summary."""
    s = get_session(session_id)
    plant_label, plant_msg = STAGE_PLANT_MESSAGES.get(s.plant_stage, STAGE_PLANT_MESSAGES[1])
    earned_badges = [BADGES[b] for b in s.badges if b in BADGES]

    return {
        "session_id": session_id,
        "player_name": s.player_name,
        "mood": s.mood,
        "current_stage": s.current_stage,
        "stages_completed": s.stages_completed,
        "plant": {"stage": plant_label, "message": plant_msg},
        "badges": earned_badges,
        "streak_days": s.streak_days,
        "total_score": s.score_total,
    }