import os
import time
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHANNEL_ID  = os.environ["CHANNEL_ID"]
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "300"))

TWITTER_USER = "FabrizioRomano"
SEEN_FILE    = "seen_posts.json"

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
    "https://nitter.privacydev.net",
    "https://nitter.kavin.rocks",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-1000:], f)

def post_id(text):
    return hashlib.md5(text[:150].encode("utf-8")).hexdigest()

def fetch_rss(host):
    url = f"{host}/{TWITTER_USER}/rss"
    r = requests.get(url, timeout=20, headers=HEADERS)
    if r.status_code != 200:
        return []
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return []
    tweets = []
    for item in root.findall(".//item"):
        desc = item.findtext("description") or ""
        title = item.findtext("title") or ""
        soup = BeautifulSoup(desc, "html.parser")
        text = soup.get_text(separator=" ").strip()
        if not text:
            text = title.strip()
        if text.lower().startswith("rt @"):
            continue
        if len(text) > 15:
            tweets.append(text)
    return tweets

def fetch_html(host):
    url = f"{host}/{TWITTER_USER}"
    r = requests.get(url, timeout=20, headers=HEADERS)
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
            if len(text) > 15:
                tweets.append(text)
    return tweets

def get_tweets():
    for host in NITTER_HOSTS:
        # RSS sinab ko'r
        try:
            tweets = fetch_rss(host)
            if tweets:
                print(f"OK RSS {host}: {len(tweets)} post")
                return tweets
        except Exception as e:
            print(f"RSS xato {host}: {e}")
        # HTML sinab ko'r
        try:
            tweets = fetch_html(host)
            if tweets:
                print(f"OK HTML {host}: {len(tweets)} post")
                return tweets
        except Exception as e:
            print(f"HTML xato {host}: {e}")
    print("Hech bir server ishlamadi")
    return []

def translate_uz(text):
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "uz", "dt": "t", "q": text},
            timeout=15
        )
        r.raise_for_status()
        return "".join(p[0] for p in r.json()[0] if p[0])
    except Exception as e:
        print(f"Tarjima xato: {e}")
        return None

def send_telegram(original, translated):
    here = "🟢 <b>HERE WE GO!</b>\n\n" if "here we go" in original.lower() else ""
    msg = (
        f"⚽ <b>Fabrizio Romano</b>\n\n"
        f"{here}"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>\n\n"
        f"<a href='https://twitter.com/FabrizioRomano'>@FabrizioRomano</a>"
    )
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": msg,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15
    )
    ok = r.status_code == 200
    if not ok:
        print(f"Telegram xato: {r.text[:150]}")
    return ok

def main():
    print("=" * 45)
    print("Fabrizio Romano Bot ishga tushdi")
    print(f"Kanal: {CHANNEL_ID}")
    print(f"Har {CHECK_EVERY // 60} daqiqada tekshiradi")
    print("=" * 45)

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
                translated = translate_uz(tweet)
                if not translated:
                    continue
                if send_telegram(tweet, translated):
                    seen.add(pid)
                    new_count += 1
                    print(f"Yuborildi: {tweet[:60]}...")
                    time.sleep(3)

            if first_run:
                print(f"Birinchi ishga tushish: {len(tweets)} post belgilandi")
                first_run = False
            elif new_count == 0:
                print("Yangi post yoq")
            else:
                print(f"{new_count} ta post yuborildi")

            save_seen(seen)

        except Exception as e:
            print(f"Xato: {e}")

        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
