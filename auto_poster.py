import os
import time
import random
import json
import requests
import openai
from requests.auth import HTTPBasicAuth

# ————— Configuration —————
WP_URL      = "https://whellthyvibe.com"
WP_USER     = "autoai"
WP_PASSWORD = "bhUj b0Og Yk5N jO9z 5l3B ix2N"

# Load OpenAI key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment")
openai.api_key = OPENAI_API_KEY

API_BASE = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
auth     = HTTPBasicAuth(WP_USER, WP_PASSWORD)

# ————— Initial Topics —————
TOPICS = [
    "Proper nutrition for athletes",
    "Effective home workouts",
    "Beginner fitness routines",
    "Cardio training for endurance",
    "Bodyweight exercises",
    "Core workouts at home",
    "Daily exercise schedule",
    "Mental health through sport",
    "Post-workout recovery strategies",
    "Importance of sleep for athletes",
    "Hydration strategies",
    "Flexibility and stretching routines",
    "HIIT vs. steady-state cardio",
    "Strength training fundamentals",
    "Mind-body connection in exercise",
    "Fitness tech gadgets overview",
    "Plant-based diets for athletes",
    "Injury prevention tips",
    "Outdoor vs. indoor workouts"
]

STATE_FILE = "used_topics.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_state(used):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

def refresh_topics():
    prompt = (
        "Generate 15 fresh, distinct blog post topics about fitness, health and sports. "
        "Return only a JSON array of strings."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
        max_tokens=200
    )
    return json.loads(resp.choices[0].message.content)

def pick_topic():
    global TOPICS
    used   = load_state()
    unused = [t for t in TOPICS if t not in used]
    if not unused:
        # list exhausted → fetch new topics
        TOPICS = refresh_topics()
        used    = []
        unused  = TOPICS.copy()
    topic = random.choice(unused)
    used.append(topic)
    save_state(used)
    return topic

def generate_text(topic: str) -> str:
    prompt = (
        f"Write a detailed, 600–800 word blog post in English about: {topic}. "
        "Include an introduction, conclusion, nutrition tips, exercise advice, and health benefits."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def generate_image(topic: str) -> str:
    try:
        img = openai.Image.create(
            prompt=f"{topic}, healthy sports photo, high resolution",
            n=1,
            size="1024x1024"
        )
        url = img.data[0].url
    except Exception:
        url = "https://source.unsplash.com/1024x1024/?fitness,health"
    fn = f"{int(time.time())}.jpg"
    r = requests.get(url, timeout=15); r.raise_for_status()
    with open(fn, "wb") as f:
        f.write(r.content)
    return fn

def upload_media(path: str) -> int:
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as img_fd:
        r = requests.post(
            f"{API_BASE}/media",
            auth=auth,
            headers={"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'},
            files={"file": img_fd}
        )
    r.raise_for_status()
    return r.json().get("id")

def create_post(title: str, content: str, media_id: int=None):
    data = {"title": title, "content": content, "status": "publish"}
    if media_id:
        data["featured_media"] = media_id
    r = requests.post(f"{API_BASE}/posts", auth=auth, json=data)
    r.raise_for_status()
    print(f"Posted: {title}")

def job():
    topic   = pick_topic()
    print(f"Generating post on: {topic}")
    text     = generate_text(topic)
    img_path = generate_image(topic)
    media_id = upload_media(img_path)
    img_tag  = (
        f'<img src="{WP_URL}/wp-content/uploads/{os.path.basename(img_path)}" '
        f'alt="{topic}" />\n\n'
        if media_id else ""
    )
    create_post(topic, img_tag + text, media_id)

if __name__ == "__main__":
    job()
