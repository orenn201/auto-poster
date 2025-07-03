import os
import json
import time
import random
import requests
import openai
import schedule
from requests.auth import HTTPBasicAuth

# Configuration
WP_URL = "https://whellthyvibe.com"
WP_USER = "autoai"
WP_PASSWORD = "bhUj b0Og Yk5N jO9z 5l3B ix2N"
OPENAI_API_KEY = "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"
API_BASE = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
STATE_FILE = "topics_state.json"

# Initialize OpenAI and authentication
openai.api_key = OPENAI_API_KEY
auth = HTTPBasicAuth(WP_USER, WP_PASSWORD)

# List of topics to post, rotates without repeats
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
    "Importance of sleep for athletes"
]

# Load or initialize remaining topics
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            remaining_topics = json.load(f)
    except Exception:
        remaining_topics = TOPICS.copy()
else:
    remaining_topics = TOPICS.copy()

# Save remaining topics state
def save_state():
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(remaining_topics, f)

# Pick next topic without repeats
def pick_topic():
    global remaining_topics
    if not remaining_topics:
        remaining_topics = TOPICS.copy()
    topic = random.choice(remaining_topics)
    remaining_topics.remove(topic)
    save_state()
    return topic

# Generate post text
def generate_text(topic: str) -> str:
    prompt = (
        f"Write a detailed, 600-800 word blog post in English about: {topic}. "
        "Include an introduction, conclusion, nutrition tips, exercise advice, and health benefits."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

# Generate or fetch image
def generate_image(topic: str) -> str:
    try:
        resp = openai.Image.create(
            prompt=f"{topic}, healthy sports photo, high resolution",
            n=1, size="1024x1024"
        )
        url = resp.data[0].url
    except Exception:
        url = "https://source.unsplash.com/1024x1024/?fitness,health"
    filename = f"{int(time.time())}.jpg"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with open(filename, 'wb') as img:
        img.write(r.content)
    return filename

# Upload media to WordPress
def upload_media(file_path: str) -> int:
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, 'rb') as img:
        resp = requests.post(
            f"{API_BASE}/media",
            auth=auth,
            headers={"Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"'},
            files={"file": img}
        )
    resp.raise_for_status()
    return resp.json().get('id')

# Create WordPress post
def create_post(title: str, content: str, media_id: int = None):
    payload = {"title": title, "content": content, "status": "publish"}
    if media_id:
        payload["featured_media"] = media_id
    resp = requests.post(
        f"{API_BASE}/posts", auth=auth, json=payload
    )
    resp.raise_for_status()
    print(f"Posted: {title}")

# Main job
def job():
    topic = pick_topic()
    print(f"Selected topic: {topic}")
    text = generate_text(topic)
    img_path = generate_image(topic)
    media_id = upload_media(img_path)
    if img_path and media_id:
        img_url = f"{WP_URL}/wp-content/uploads/{os.path.basename(img_path)}"
        content = f'<img src="{img_url}" alt="{topic}" />\n\n{text}'
    else:
        content = text
    create_post(topic, content, media_id)

# Run immediately and schedule hourly
if __name__ == '__main__':
    job()
    schedule.every().hour.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
