import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHANNEL_ID  = "-1003483897290"
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "10"))

SEEN = set()

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
    "https://nitter.privacydev.net",
    "https://nitter.kavin.rocks",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_tweets():
    for host in NITTER_HOSTS:
        try:
            r = requests.get(f"{host}/FabrizioRomano", timeout=15, headers=HEADERS)
            if r.status_code != 200:
                print(f"Skip {host}: status {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            tweets = []
            for item in soup.select(".timeline-item"):
                if item.select_one(".retweet-header"):
                    continue
                content = item.select_one(".tweet-content")
                if content:
                    text = content.get_text(" ").strip()
                    if len(text) > 15:
                        tweets.append(text)
            if tweets:
                print(f"OK {host}: {len(tweets)} post")
                return tweets
            print(f"Skip {host}: post topilmadi")
        except Exception as e:
            print(f"Xato {host}: {e}")
    return []

def translate(text):
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "uz", "dt": "t", "q": text},
            timeout=15
        )
        return "".join(p[0] for p in r.json()[0] if p[0])
    except Exception as e:
        print(f"Tarjima xato: {e}")
        return None

def send(original, translated):
   print(f"Yuborilayapti: chat_id={CHANNEL_ID}")
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
    print(f"Telegram xato: {r.text[:150]}")
    return False

def main():
    global SEEN
    print(f"Bot ishga tushdi | Kanal: {CHANNEL_ID}")
    print(f"Har {CHECK_EVERY//60} daqiqada tekshiradi")

    # Birinchi ishganda mavjud postlarni belgilab qo'y
    tweets = get_tweets()
    print(f"Birinchi ishga tushish: {len(tweets)} post belgilandi, yangilarini kutmoqda...")

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
            print(f"{new} ta yangi post yuborildi" if new else "Yangi post yoq")
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    main()
