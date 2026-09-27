import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from google import genai

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = f"sqlite:///{BASE_DIR / 'fitbuddy.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(String(30), nullable=False)
    goal = Column(String(50), nullable=False)
    intensity = Column(String(20), nullable=False)
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True)
    nutrition_tip = Column(Text, nullable=False)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FitBuddy - AI Fitness Plan Generator")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def demo_plan(goal: str, intensity: str) -> str:
    return f"""7-DAY FITBUDDY WORKOUT PLAN
Goal: {goal.title()} | Intensity: {intensity.title()}

Day 1 - Full Body
Warm-up: 5-10 minutes brisk walking
Main: Squats 3x12, Push-ups 3x10, Rows 3x12
Cooldown: 5 minutes stretching

Day 2 - Cardio
Warm-up: 5 minutes
Main: Brisk walk/jog 25 minutes + 3x30 sec faster intervals
Cooldown: 5 minutes

Day 3 - Lower Body
Warm-up: 5-10 minutes
Main: Lunges 3x10/leg, Glute bridges 3x15, Calf raises 3x15
Cooldown: 5 minutes

Day 4 - Recovery
Light walking 20 minutes + mobility/stretching 10 minutes

Day 5 - Upper Body
Warm-up: 5 minutes
Main: Push-ups 3x10, Shoulder press 3x12, Rows 3x12
Cooldown: 5 minutes

Day 6 - Core + Cardio
Main: Plank 3x30 sec, Dead bug 3x10/side, Cardio 20 minutes
Cooldown: 5 minutes

Day 7 - Rest / Active Recovery
Easy walk and gentle stretching.

Adjust exercise difficulty to your experience and stop if you feel pain."""

def demo_tip(goal: str) -> str:
    tips = {
        "muscle gain": "Include a protein source in each meal and stay hydrated. Good options include eggs, fish, chicken, beans, or Greek yogurt.",
        "weight loss": "Prioritize protein, vegetables, whole foods and adequate water. Keep portions consistent and avoid relying on sugary drinks.",
        "general wellness": "Aim for balanced meals, adequate hydration, regular sleep, and a variety of fruits, vegetables and protein sources.",
    }
    return tips.get(goal.lower(), "Stay hydrated and include balanced meals with protein, vegetables and whole foods.")

def gemini_text(prompt: str) -> str:
    if DEMO_MODE or client is None:
        return ""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return (response.text or "").strip()

def generate_plan(username, age, weight, goal, intensity):
    prompt = f"""
You are FitBuddy, an AI fitness planning assistant.
Create a practical personalized 7-day workout plan.

User:
Name: {username}
Age: {age}
Weight: {weight} kg
Goal: {goal}
Intensity: {intensity}

Format exactly as a readable day-by-day plan.
For each day include focus, warm-up, exercises with sets/reps or duration,
and cooldown/recovery guidance. Keep it realistic and concise.
Do not claim to diagnose or treat medical conditions.
"""
    try:
        text = gemini_text(prompt)
        return text or demo_plan(goal, intensity)
    except Exception:
        return demo_plan(goal, intensity)

def generate_tip(goal):
    prompt = f"""Give one concise, practical nutrition or recovery tip for a fitness user whose goal is {goal}.
Mention hydration/protein or another relevant healthy habit. Avoid medical claims."""
    try:
        text = gemini_text(prompt)
        return text or demo_tip(goal)
    except Exception:
        return demo_tip(goal)

def update_plan(original_plan, feedback):
    prompt = f"""
Update this FitBuddy workout plan using the user's feedback.

ORIGINAL PLAN:
{original_plan}

USER FEEDBACK:
{feedback}

Return a complete revised 7-day plan, not just a list of changes.
Keep the plan practical and clearly structured by day.
"""
    try:
        text = gemini_text(prompt)
        return text or (original_plan + "\n\nUPDATED BASED ON FEEDBACK:\n" + feedback)
    except Exception:
        return original_plan + "\n\nUPDATED BASED ON FEEDBACK:\n" + feedback

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@app.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight: str = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
):
    plan = generate_plan(username, age, weight, goal, intensity)
    tip = generate_tip(goal)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.user_id == user_id).first()
        if existing:
            existing.username = username
            existing.age = age
            existing.weight = weight
            existing.goal = goal
            existing.intensity = intensity
            existing.original_plan = plan
            existing.updated_plan = None
            existing.nutrition_tip = tip
        else:
            db.add(User(
                user_id=user_id, username=username, age=age, weight=weight,
                goal=goal, intensity=intensity, original_plan=plan, nutrition_tip=tip
            ))
        db.commit()
    finally:
        db.close()

    return templates.TemplateResponse(
        request=request, name="result.html",
        context={"username": username, "user_id": user_id, "age": age, "weight": weight,
                  "goal": goal, "intensity": intensity, "workout_plan": plan,
                  "nutrition_tip": tip, "updated_plan": None}
    )

@app.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return templates.TemplateResponse(
                request=request, name="error.html",
                context={"message": "User ID not found. Please generate a plan first."}
            )
        revised = update_plan(user.original_plan, feedback)
        user.updated_plan = revised
        db.commit()
        return templates.TemplateResponse(
            request=request, name="result.html",
            context={"username": user.username, "user_id": user.user_id, "age": user.age,
                     "weight": user.weight, "goal": user.goal, "intensity": user.intensity,
                     "workout_plan": user.original_plan, "nutrition_tip": user.nutrition_tip,
                     "updated_plan": revised, "feedback": feedback}
        )
    finally:
        db.close()

@app.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.desc()).all()
        return templates.TemplateResponse(request=request, name="all_users.html", context={"users": users})
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL, "demo_mode": DEMO_MODE, "gemini_configured": bool(client)}

@app.get("/docs-link", include_in_schema=False)
def docs_link():
    return RedirectResponse("/docs")
