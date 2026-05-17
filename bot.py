import os
import time
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# ── Sozlamalar ────────────────────────────────────────────────
BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHANNEL_ID  = os.environ["CHANNEL_ID"]
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "600"))

TWITTER_USER = "FabrizioRomano"
SEEN_FILE    = "seen_posts.json"

NITTER_HOSTS = [
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
    "https://xcancel.com",
    "https://nitter.privacydev.net",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-500:], f)

def post_id(text):
    return hashlib.md5(text[:120].encode()).hexdigest()

def fetch_via_nitter_rss(host):
    url = f"{host}/{TWITTER_USER}/rss"
    r = requests.get(url, timeout=15, headers=HEADERS)
    if r.status_code != 200:
        return []
    root = ET.fromstring(r.content)
    tweets = []
    for item in root.findall(".//item"):
        desc = item.findtext("description") or ""
        title = item.findtext("title") or ""
        soup = BeautifulSoup(desc, "html.parser")
        text = soup.get_text(separator=" ").strip()
        if not text:
            text = title.strip()
        if text.startswith("RT @"):
            continue
        if text and len(text) > 10:
            tweets.append(text)
    return tweets

def fetch_via_nitter_html(host):
    url = f"{host}/{TWITTER_USER}"
    r = requests.get(url, timeout=15, headers=HEADERS)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    tweets = []
    for item in soup.select(".timeline-item"):
        if item.select_one(".retweet-header"):
            continue
        content = item.select_one(".tweet-content")
        if content:
            text = content.get_text(separator=" ").strip()
            if text and len(text) > 10:
                tweets.append(text)
    return tweets

def get_tweets():
    for host in NITTER_HOSTS:
        try:
            tweets = fetch_via_nitter_rss(host)
            if tweets:
                print(f"OK RSS: {host} — {len(tweets)} ta post")
                return tweets
        except Exception as e:
            print(f"   RSS xato {host}: {e}")
        try:
            tweets = fetch_via_nitter_html(host)
            if tweets:
                print(f"OK HTML: {host} — {len(tweets)} ta post")
                return tweets
        except Exception as e:
            print(f"   HTML xato {host}: {e}")
    print("Hech bir server ishlamadi")
    return []

def translate_to_uzbek(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "uz", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return "".join(part[0] for part in data[0] if part[0])
    except Exception as e:
        print(f"Tarjima xatosi: {e}")
        return None

def send_to_telegram(original, translated):
    here_we_go = "🟢 <b>HERE WE GO!</b>\n" if "here we go" in original.lower() else ""
    message = (
        f"⚽ <b>Fabrizio Romano</b>\n"
        f"{here_we_go}\n"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>\n\n"
        f"<a href='https://twitter.com/FabrizioRomano'>@FabrizioRomano</a>"
    )
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": message,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )
    if r.status_code == 200:
        print(f"Yuborildi: {original[:70]}...")
        return True
    print(f"Telegram xato: {r.status_code} — {r.text[:100]}")
    return False

def main():
    print("=" * 50)
    print("Fabrizio Romano Transfer Bot")
    print(f"Kanal: {CHANNEL_ID}")
    print(f"Har {CHECK_EVERY // 60} daqiqada tekshiradi")
    print("=" * 50)

    seen = load_seen()
    first_run = len(seen) == 0

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tekshirilmoqda...")
        try:
            tweets = get_tweets()
            new_count = 0
            for tweet in tweets:
                pid = post_id(tweet)
                if pid in seen:
                    continue
                if first_run:
                    seen.add(pid)
                    continue
                translated = translate_to_uzbek(tweet)
                if not translated:
                    continue
                if send_to_telegram(tweet, translated):
                    seen.add(pid)
                    new_count += 1
                    time.sleep(3)

            if first_run:
                print(f"Birinchi ishga tushish: {len(tweets)} ta post belgilandi")
                first_run = False
            elif new_count == 0:
                print("Yangi post yoq")
            else:
                print(f"{new_count} ta yangi post yuborildi")

            save_seen(seen)
        except Exception as e:
            print(f"Xato: {e}")

        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
