import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

BOT_TOKEN  = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "300"))

SEEN = set()

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_tweets():
    for host in NITTER_HOSTS:
        try:
            url = f"{host}/FabrizioRomano/rss"
            r = requests.get(url, timeout=15, headers=HEADERS)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            tweets = []
            for item in root.findall(".//item"):
                desc = item.findtext("description") or ""
                text = BeautifulSoup(desc, "html.parser").get_text(" ").strip()
                if not text:
                    text = (item.findtext("title") or "").strip()
                if text and not text.startswith("RT @") and len(text) > 15:
                    tweets.append(text)
            if tweets:
                print(f"OK: {host} — {len(tweets)} post")
                return tweets
        except Exception as e:
            print(f"Xato {host}: {e}")
    return []

def translate(text):
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client":"gtx","sl":"en","tl":"uz","dt":"t","q":text},
            timeout=15
        )
        return "".join(p[0] for p in r.json()[0] if p[0])
    except:
        return None

def send(original, translated):
    icon = "🟢 <b>HERE WE GO!</b>\n\n" if "here we go" in original.lower() else ""
    text = (
        f"⚽ <b>Fabrizio Romano</b>\n\n"
        f"{icon}"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>"
    )
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15
    )
    if r.status_code == 200:
        print(f"Yuborildi: {original[:60]}")
        return True
    print(f"Telegram xato: {r.text[:100]}")
    return False

def main():
    global SEEN
    print(f"Bot ishga tushdi | Kanal: {CHANNEL_ID}")

    # Birinchi ishganda mavjud postlarni belgilab qo'y
    tweets = get_tweets()
    for t in tweets:
        SEEN.add(t[:100])
    print(f"Birinchi ishga tushish: {len(tweets)} post belgilandi")

    while True:
        time.sleep(CHECK_EVERY)
        print(f"\n[{datetime.now().strftime('%H:%M')}] Tekshirilmoqda...")
        try:
            tweets = get_tweets()
            new = 0
            for tweet in tweets:
                key = tweet[:100]
                if key in SEEN:
                    continue
                tr = translate(tweet)
                if tr and send(tweet, tr):
                    SEEN.add(key)
                    new += 1
                    time.sleep(2)
            print(f"{new} ta yangi post" if new else "Yangi post yoq")
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    main()
