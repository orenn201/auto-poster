import os
import time
import json
import random
import requests
import openai
import schedule
from requests.auth import HTTPBasicAuth
from httpx import ConnectError, ReadTimeout, HTTPError as HTTPXError

# Configuration
WP_URL         = "https://whellthyvibe.com"
WP_USER        = "autoai"
WP_PASSWORD    = "bhUj b0Og Yk5N jO9z 5l3B ix2N"
OPENAI_API_KEY = "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"
API_BASE       = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
STATE_FILE     = "used_topics.json"

openai.api_key = OPENAI_API_KEY
auth = HTTPBasicAuth(WP_USER, WP_PASSWORD)

# Load or initialize used topics
if os.path.exists(STATE_FILE):
    used_topics = set(json.load(open(STATE_FILE)))
else:
    used_topics = set()


def save_used():
    with open(STATE_FILE, "w") as f:
        json.dump(list(used_topics), f)


def suggest_topic() -> str:
    for _ in range(5):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":"Suggest a unique blog post topic about fitness or healthy living."}],
                max_tokens=20,
                temperature=0.8
            )
            topic = resp.choices[0].message.content.strip()
            if topic and topic not in used_topics:
                used_topics.add(topic)
                save_used()
                return topic
        except (ConnectError, ReadTimeout, HTTPXError):
            time.sleep(2)
        except Exception:
            break
    fallback = f"General fitness tip #{len(used_topics)+1}"
    used_topics.add(fallback)
    save_used()
    return fallback


def generate_text(topic: str) -> str:
    prompt = (
        f"Write a detailed, 600–800 word blog post in English on: {topic}. Include intro, conclusion, tips, and benefits."
    )
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=800,
            temperature=0.7
        )
        return resp.choices[0].message.content
    except Exception:
        return "Content temporarily unavailable."


def fetch_image(topic: str) -> str:
    try:
        resp = openai.images.generate(
            prompt=f"{topic}, healthy sports photo",
            n=1,
            size="1024x1024"
        )
        url = resp.data[0].url
    except Exception:
        url = "https://source.unsplash.com/1024x1024/?fitness,health"
    filename = f"{int(time.time())}.jpg"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(filename, "wb") as f:
            f.write(r.content)
        return filename
    except Exception:
        return None


def upload_media(path: str) -> int:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as img:
            r = requests.post(
                f"{API_BASE}/media",
                auth=auth,
                headers={"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'},
                files={"file": img}
            )
        if r.status_code == 201:
            return r.json().get("id")
    except Exception:
        pass
    return None


def create_post(title: str, body: str, media_id: int):
    payload = {"title": title, "content": body, "status": "publish"}
    if media_id:
        payload["featured_media"] = media_id
    try:
        r = requests.post(f"{API_BASE}/posts", auth=auth, json=payload)
        if r.status_code not in (200, 201):
            print("Post creation failed:", r.status_code)
    except Exception as e:
        print("Post request error:", e)


def job():
    try:
        topic = suggest_topic()
        print("Topic:", topic)
        text = generate_text(topic)
        img = fetch_image(topic)
        media_id = upload_media(img) if img else None
        if img:
            body = f'<img src="{WP_URL}/wp-content/uploads/{os.path.basename(img)}"/>' + "\n\n" + text
        else:
            body = text
        create_post(topic, body, media_id)
        print("Posted:", topic)
    except Exception as e:
        print("Job error:", e)

# Schedule job every hour and run immediately once
schedule.every().hour.do(job)

if __name__ == "__main__":
    job()
    while True:
        schedule.run_pending()
        time.sleep(1)
