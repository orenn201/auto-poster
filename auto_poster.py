import os
import time
import random
import json
import requests
import openai
from PIL import Image

# ————— Configuration —————
WP_URL        = "https://whellthyvibe.com"
WP_USER       = "autoai"
WP_PASS       = "Oren_ai12345"  # הסיסמה הרגילה שלך
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")
openai.api_key = OPENAI_API_KEY

API_BASE   = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
STATE_FILE = "used_topics.json"

CATEGORIES = [
    "Nutrition", "Home Workouts", "Cardio Training", "Strength Training",
    "Flexibility & Stretching", "Mental Health & Mindfulness",
    "Sports Technology & Gadgets", "Therapeutic Sports (Yoga/Pilates)",
    "Work–Life Balance", "Outdoor Activities", "Healthy Recipes & Meal Planning",
    "Hydration Strategies", "Sleep & Recovery", "Interval Training",
    "Bodyweight Conditioning", "Kettlebell Workouts", "CrossFit Techniques",
    "Weightlifting Methods", "Running Form Analysis", "Cycling Efficiency",
    "Swimming Drills", "Sports Injuries Prevention", "Postural Alignment",
    "Mobility Drills", "Dynamic Warmups", "Cool Down Techniques",
    "Yoga for Athletes", "Pilates for Core Strength", "Tabata Protocols",
    "Sprint Training", "Marathon Preparation", "Trail Running",
    "Obstacle Course Preparation", "Functional Training", "TRX Suspension Workouts",
    "Resistance Band Exercises", "Dumbbell Routines", "Barbell Complexes",
    "Medicine Ball Drills", "Plyometrics", "Agility Ladder Drills",
    "Footwork Patterns", "Speed Endurance", "Breathwork Techniques",
    "Mindfulness Meditation", "Sports Psychology", "Goal Setting Strategies",
    "Habit Formation", "Nutrition Timing", "Macro Tracking",
    "Micro Nutrients", "Supplement Science", "Plant-Based Performance",
    "Ketogenic Diet for Athletes", "Intermittent Fasting Effects",
    "Recovery Nutrition", "Sleep Hygiene", "Circadian Rhythm Optimization",
    "Cold Water Immersion", "Sauna Benefits", "Massage Techniques",
    "Foam Rolling", "Trigger Point Therapy", "Active Recovery", "Deload Weeks",
    "Mental Toughness Drills", "Visualization Techniques", "Biohacking Devices",
    "Wearable Tech Reviews", "Fitness Apps Comparison", "Home Gym Setup",
    "Gear Maintenance", "Footwear Selection", "Heart Rate Monitoring",
    "GPS Watch Tips", "HIIT Variations", "EMOM Workouts", "AMRAP Strategies",
    "Charity Runs Organization", "Outdoor Adventure Activities", "Beach Workouts",
    "Urban Fitness", "Parkour Basics", "Dance-Based Fitness", "Kids Fitness Games",
    "Senior Fitness Programs", "Prenatal Fitness", "Postnatal Recovery",
    "Adaptive Sports", "E-Sports Ergonomics", "Workplace Wellness",
    "Office Stretch Breaks", "Digital Detox", "Virtual Trainer Platforms",
    "Group Fitness Dynamics", "Sports Event Planning", "Fitness Community Building",
    "Mobile Health Monitoring", "Personalized Coaching AI", "Recovery Wearable Technology"
]

def get_jwt_token() -> str:
    resp = requests.post(
        f"{WP_URL}/wp-json/jwt-auth/v1/token",
        json={"username": WP_USER, "password": WP_PASS},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()["token"]

def jwt_headers() -> dict:
    token = get_jwt_token()
    return {"Authorization": f"Bearer {token}"}

def load_state() -> list:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_state(used: list):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

def pick_topic() -> str:
    used = load_state()
    cat = random.choice(CATEGORIES)
    prompt = (
        f"Within the category \"{cat}\", suggest a specific, deep-dive blog post topic. "
        "Do NOT repeat already used topics:\n" +
        "\n".join(f"- {t}" for t in used) +
        "\nRespond with the topic only."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
        max_tokens=30
    )
    topic = resp.choices[0].message.content.strip().strip('"')
    if not topic or topic in used:
        topic = f"{cat} Insight #{len(used)+1}"
    full = f"[{cat}] {topic}"
    used.append(full)
    save_state(used)
    return topic

def generate_meta(topic: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":
            f"Write a 140–160 character meta description for a post about: {topic}."}],
        temperature=0.6,
        max_tokens=60
    )
    return resp.choices[0].message.content.strip().strip('"')

def generate_text(topic: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":
            f"Write a detailed 600–800 word blog post about: {topic}. "
            "Include an introduction, subheadings, nutrition tips, exercise advice, health benefits "
            "and end with a strong concluding paragraph."}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def generate_image(topic: str) -> str:
    try:
        img = openai.Image.create(
            prompt=f"{topic}, photorealistic, sharp focus, no text",
            n=1, size="1024x1024"
        )
        url = img.data[0].url
    except:
        keywords = topic.replace(" ", ",")
        url = f"https://source.unsplash.com/1024x1024/?{keywords},fitness"
    fn = f"{int(time.time())}.jpg"
    r = requests.get(url, timeout=15); r.raise_for_status()
    with open(fn, "wb") as f:
        f.write(r.content)
    im = Image.open(fn)
    im.thumbnail((1024,1024), Image.LANCZOS)
    canvas = Image.new("RGB",(1024,1024),(255,255,255))
    canvas.paste(im, ((1024-im.width)//2, (1024-im.height)//2))
    canvas.save(fn)
    return fn

def upload_media(path: str):
    if not os.path.exists(path):
        return None
    try:
        hdr = jwt_headers()
        with open(path, "rb") as fd:
            r = requests.post(
                f"{API_BASE}/media",
                headers={**hdr, "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'},
                files={"file": fd},
                timeout=30
            )
        if r.status_code == 401:
            print("⚠️ media upload unauthorized, skipping image.")
            return None
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"⚠️ upload_media failed: {e}")
        return None

def create_post(title: str, content: str, excerpt: str, focus_kw: str, media_id):
    hdr = {**jwt_headers(), "Content-Type":"application/json"}
    payload = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "status": "publish",
        "meta": {
            "_yoast_wpseo_metadesc": excerpt,
            "_yoast_wpseo_focuskw": focus_kw,
        }
    }
    if media_id:
        payload["featured_media"] = media_id
    r = requests.post(f"{API_BASE}/posts", headers=hdr, json=payload, timeout=30)
    r.raise_for_status()
    print("✅ Posted:", title)

def job():
    topic = pick_topic()
    print("Topic:", topic)
    meta  = generate_meta(topic)
    text  = generate_text(topic)
    imgp  = generate_image(topic)
    mid   = upload_media(imgp)
    create_post(topic, text, meta, topic, mid)

if __name__ == "__main__":
    job()
