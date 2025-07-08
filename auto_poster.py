import os, time, random, json, requests, openai
from PIL import Image

# ————— Configuration —————
WP_URL      = "https://whellthyvibe.com"
WP_USER     = "autoai"
WP_PASS     = "Oren_ai12345"  # הסיסמה הרגילה שלך
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")
openai.api_key = OPENAI_API_KEY

API_BASE   = f"{WP_URL.rstrip('/')}/wp-json/wp/v2"
STATE_FILE = "used_topics.json"
CATEGORIES = [ ... ]  # הרשימה שלך

def get_jwt_token():
    resp = requests.post(
        f"{WP_URL}/wp-json/jwt-auth/v1/token",
        json={"username": WP_USER, "password": WP_PASS},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()["token"]

def jwt_headers():
    token = get_jwt_token()
    return {
        "Authorization": f"Bearer {token}"
    }

def load_state():
    return json.load(open(STATE_FILE, encoding="utf-8")) if os.path.exists(STATE_FILE) else []

def save_state(used):
    json.dump(used, open(STATE_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

def pick_topic():
    used = load_state()
    cat  = random.choice(CATEGORIES)
    prompt = (
        f"Within the category \"{cat}\", suggest a specific deep-dive blog post topic. "
        "Do NOT repeat already used topics:\n"
        + "\n".join(f"- {t}" for t in used)
        + "\nRespond with topic only."
    )
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8, max_tokens=30
    )
    topic = r.choices[0].message.content.strip().strip('"')
    if not topic or topic in used:
        topic = f"{cat} Insight #{len(used)+1}"
    full = f"[{cat}] {topic}"
    used.append(full); save_state(used)
    return topic

def generate_meta(topic):
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user",
                   "content":f"Write a 140-160 char meta description for: {topic}."}],
        temperature=0.6, max_tokens=60
    )
    return r.choices[0].message.content.strip().strip('"')

def generate_text(topic):
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":
            f"Write a detailed 600-800 word blog post about: {topic}. "
            "Include intro, conclusion, tips & benefits."}],
        temperature=0.7, max_tokens=800
    )
    return r.choices[0].message.content.strip()

def generate_image(topic):
    try:
        img = openai.Image.create(
            prompt=f"{topic}, photo of exercise, no text",
            n=1, size="1024x1024"
        )
        url = img.data[0].url
    except:
        url = f"https://source.unsplash.com/1024x1024/?{topic.replace(' ','%20')},fitness"
    fn = f"{int(time.time())}.jpg"
    r = requests.get(url, timeout=15); r.raise_for_status()
    with open(fn,"wb") as f: f.write(r.content)
    im = Image.open(fn)
    im.thumbnail((1024,1024), Image.LANCZOS)
    canvas = Image.new("RGB",(1024,1024),(255,255,255))
    canvas.paste(im, ((1024-im.width)//2, (1024-im.height)//2))
    canvas.save(fn)
    return fn

def upload_media(path):
    if not os.path.exists(path): return None
    try:
        hdr = jwt_headers()
        with open(path,"rb") as fd:
            r = requests.post(f"{API_BASE}/media",
                              headers={**hdr,
                                       "Content-Disposition":
                                       f'attachment; filename="{os.path.basename(path)}"'},
                              files={"file": fd}, timeout=30)
        if r.status_code==401:
            print("⚠️ media upload unauthorized")
            return None
        r.raise_for_status()
        return r.json()["id"]
    except Exception as e:
        print("⚠️ upload_media failed:", e)
        return None

def create_post(title, content, excerpt, focus, media_id):
    hdr = {**jwt_headers(), "Content-Type":"application/json"}
    data = {
        "title":title,"content":content,"excerpt":excerpt,
        "status":"publish","meta":{
            "_yoast_wpseo_metadesc":excerpt,
            "_yoast_wpseo_focuskw":focus
        }
    }
    if media_id: data["featured_media"]=media_id
    r = requests.post(f"{API_BASE}/posts", headers=hdr, json=data, timeout=30)
    r.raise_for_status()
    print("✅ Posted:", title)

def job():
    topic = pick_topic(); print("Topic:",topic)
    meta  = generate_meta(topic)
    txt   = generate_text(topic)
    imgp  = generate_image(topic)
    mid   = upload_media(imgp)
    create_post(topic, f'<img src="{WP_URL}/wp-content/uploads/{os.path.basename(imgp)}"/> \n\n'+txt,
                meta, topic, mid)

if __name__=="__main__":
    job()
