import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re

BOT_TOKEN   = "8153557967:AAHk4EoCSoh-PIkcFljqEzVKv_FgXyDLS-Q"
CHANNEL_ID  = "-1003483897290"
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "300"))

SEEN = set()

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
}

KEEP_WORDS = [
    "Real Madrid", "Barcelona", "Manchester United", "Manchester City",
    "Liverpool", "Chelsea", "Arsenal", "Tottenham", "Bayern Munich",
    "PSG", "Juventus", "AC Milan", "Inter Milan", "Napoli",
    "Atletico Madrid", "Borussia Dortmund", "Premier League",
    "La Liga", "Serie A", "Bundesliga", "Champions League",
    "Europa League", "HERE WE GO", "Here we go", "done deal",
    "Aston Villa", "Newcastle", "West Ham", "Everton", "Leicester",
    "Roma", "Lazio", "Fiorentina", "Sevilla", "Valencia",
    "RB Leipzig", "Bayer Leverkusen", "Porto", "Benfica", "Ajax",
]

def protect_words(text):
    placeholders = {}
    for i, word in enumerate(KEEP_WORDS):
        if word.lower() in text.lower():
            placeholder = f"XXWORD{i}XX"
            placeholders[placeholder] = word
            text = re.sub(re.escape(word), placeholder, text, flags=re.IGNORECASE)
    return text, placeholders

def restore_words(text, placeholders):
    for placeholder, word in placeholders.items():
        text = text.replace(placeholder, word)
    return text

def translate(text):
    try:
        protected, placeholders = protect_words(text)
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "uz", "dt": "t", "q": protected},
            timeout=15
        )
        translated = "".join(p[0] for p in r.json()[0] if p[0])
        result = restore_words(translated, placeholders)
        for wrong in ["Mana, ketdik!", "Bu yerga boring!", "Mana boring!", "Keling!", "Mana ket!", "Mana keting!"]:
            result = result.replace(wrong, "HERE WE GO!")
        return result
    except Exception as e:
        print(f"Tarjima xato: {e}")
        return None

def get_images_from_nitter(item, host):
    """Nitter dan rasm URL larini olish"""
    images = []
    for img in item.select("img"):
        src = img.get("src", "")
        if not src:
            continue
        # Nitter rasm linklari /pic/ yoki /media/ bilan boshlanadi
        if src.startswith("/pic/") or src.startswith("/media/"):
            full = host + src
            images.append(full)
        elif "pbs.twimg.com" in src or "twimg.com" in src:
            images.append(src)
    return images

def get_tweet_link(item, host):
    """Post linkini olish"""
    link = item.select_one(".tweet-link, a.tweet-date")
    if link:
        href = link.get("href", "")
        if href.startswith("/"):
            return f"https://twitter.com{href}"
        return href
    return "https://twitter.com/FabrizioRomano"

def get_tweets():
    for host in NITTER_HOSTS:
        try:
            r = requests.get(f"{host}/FabrizioRomano", timeout=15, headers=HEADERS)
            if r.status_code != 200:
                print(f"Skip {host}: {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            tweets = []
            for item in soup.select(".timeline-item"):
                if item.select_one(".retweet-header"):
                    continue
                content = item.select_one(".tweet-content")
                if not content:
                    continue
                text = content.get_text(" ").strip()
                if len(text) < 15:
                    continue
                images = get_images_from_nitter(item, host)
                link = get_tweet_link(item, host)
                tweets.append({"text": text, "images": images, "link": link})
            if tweets:
                print(f"OK {host}: {len(tweets)} post, rasmli: {sum(1 for t in tweets if t['images'])} ta")
                return tweets
        except Exception as e:
            print(f"Xato {host}: {e}")
    return []

def download_image(url):
    """Rasmni yuklab olish"""
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except Exception as e:
        print(f"Rasm yuklab olish xato: {e}")
    return None

def send(original, translated, images, link):
    here = "here we go" in original.lower()
    icon = "🟢 <b>HERE WE GO!</b>\n\n" if here else ""
    caption = (
        f"⚽ <b>Fabrizio Romano</b> 🇮🇹\n\n"
        f"{icon}"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>"
    )

    # Rasm bilan yuborishga urinish
    if images:
        print(f"Rasmlar topildi: {len(images)} ta — {images[0]}")
        img_data = download_image(images[0])
        if img_data:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("image.jpg", img_data, "image/jpeg")},
                timeout=20
            )
            if r.status_code == 200:
                print(f"✅ Rasm bilan yuborildi: {original[:50]}")
                return True
            print(f"Rasm yuborish xato: {r.text[:100]}")

    # Faqat matn
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHANNEL_ID, "text": caption,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15
    )
    if r.status_code == 200:
        print(f"✅ Matn yuborildi: {original[:50]}")
        return True
    print(f"Telegram xato: {r.text[:150]}")
    return False

def main():
    global SEEN
    print("=" * 50)
    print("Fabrizio Romano Bot ishga tushdi")
    print(f"Kanal: {CHANNEL_ID}")
    print(f"Har {CHECK_EVERY//60} daqiqada tekshiradi")
    print("=" * 50)

    tweets = get_tweets()
    for t in tweets:
        SEEN.add(t["text"][:100])
    print(f"Birinchi ishga tushish: {len(tweets)} post belgilandi")
    print("Yangi postlar kutilmoqda...")

    while True:
        time.sleep(CHECK_EVERY)
        print(f"\n[{datetime.now().strftime('%H:%M')}] Tekshirilmoqda...")
        try:
            tweets = get_tweets()
            total = 0
            for tweet in tweets:
                key = tweet["text"][:100]
                if key in SEEN:
                    continue
                tr = translate(tweet["text"])
                if tr and send(tweet["text"], tr, tweet["images"], tweet["link"]):
                    SEEN.add(key)
                    total += 1
                    time.sleep(3)
            print(f"{total} ta yangi post yuborildi" if total else "Yangi post yoq")
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    main()
