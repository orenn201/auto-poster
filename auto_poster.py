import os
import time
import random
import json
import requests
import openai
from PIL import Image
from requests.auth import HTTPBasicAuth

# ————— Configuration —————
WP_URL      = "https://whellthyvibe.com"
WP_USER     = "autoai"
WP_PASSWORD = "bhUj b0Og Yk5N jO9z 5l3B ix2N"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment")
openai.api_key = OPENAI_API_KEY

API_BASE   = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
auth       = HTTPBasicAuth(WP_USER, WP_PASSWORD)
STATE_FILE = "used_topics.json"

CATEGORIES = [
    "Nutrition",
    "Home Workouts",
    "Cardio Training",
    "Strength Training",
    "Flexibility & Stretching",
    "Mental Health & Mindfulness",
    "Sports Technology & Gadgets",
    "Therapeutic Sports (Yoga/Pilates)",
    "Work–Life Balance",
    "Outdoor Activities",
    "Healthy Recipes & Meal Planning",
    "Hydration Strategies",
    "Sleep & Recovery",
]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_state(used):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)

def pick_topic():
    used = load_state()
    category = random.choice(CATEGORIES)
    prompt = (
        f"Within the category \"{category}\", suggest a specific, deep-dive blog post topic. "
        "Focus on a narrow sub-aspect (e.g. a method, a case study or an emerging trend) "
        "that has NOT been covered yet.\n"
        "Do NOT repeat any of these already used topics:\n"
        + "\n".join(f"- {t}" for t in used)
        + "\nRespond with the topic only."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
        max_tokens=30
    )
    subtopic = resp.choices[0].message.content.strip().strip('"')
    if not subtopic or any(t.endswith(subtopic) for t in used):
        subtopic = f"{category} Deep Insight #{len(used)+1}"
    full = f"[{category}] {subtopic}"
    used.append(full)
    save_state(used)
    return category, subtopic

def generate_meta_description(topic: str) -> str:
    prompt = (
        f"Write a concise 140–160 character meta description in English "
        f"for a blog post about: {topic}."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.6,
        max_tokens=60
    )
    return resp.choices[0].message.content.strip().strip('"')

def generate_text(topic: str) -> str:
    prompt = (
        f"Write a detailed, 600–800 word blog post in English about: {topic}. "
        "Include an introduction, conclusion, nutrition tips, exercise advice, and health benefits."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def generate_image(topic: str) -> str:
    try:
        prompt = (
            f"{topic}, photorealistic portrait of a person exercising, "
            "ultra-detailed, sharp focus, no text, no letters, no watermark"
        )
        img = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
        url = img.data[0].url
    except:
        keywords = topic.replace(" ", ",")
        url = f"https://source.unsplash.com/1024x1024/?{keywords},fitness"
    fn = f"{int(time.time())}.jpg"
    r  = requests.get(url, timeout=15); r.raise_for_status()
    with open(fn, "wb") as f:
        f.write(r.content)

    im = Image.open(fn)
    im.thumbnail((1024, 1024), Image.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (255, 255, 255))
    x = (1024 - im.width) // 2
    y = (1024 - im.height) // 2
    canvas.paste(im, (x, y))
    canvas.save(fn)
    return fn

def upload_media(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fd:
        r = requests.post(
            f"{API_BASE}/media",
            auth=auth,
            headers={"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'},
            files={"file": fd}
        )
    r.raise_for_status()
    return r.json().get("id")

def create_post(title, content, excerpt, focus_kw, featured_media_id):
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
    if featured_media_id:
        payload["featured_media"] = featured_media_id
    r = requests.post(f"{API_BASE}/posts", auth=auth, json=payload)
    r.raise_for_status()
    print("Posted:", title)

def job():
    category, topic = pick_topic()
    print("Category:", category)
    print("Topic:",    topic)
    meta    = generate_meta_description(topic)
    text    = generate_text(topic)
    imgp    = generate_image(topic)
    mid     = upload_media(imgp)
    create_post(topic, text, meta, topic, mid)

if __name__ == "__main__":
    job()
