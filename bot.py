import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN   = "8153557967:AAHk4EoCSoh-PIkcFljqEzVKv_FgXyDLS-Q"
CHANNEL_ID  = "-1003483897290"
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "300"))

SEEN = set()

# Kuzatiladigan manbalar
SOURCES = [
    {"user": "FabrizioRomano",   "name": "Fabrizio Romano",    "flag": "🇮🇹"},
    {"user": "David_Ornstein",   "name": "David Ornstein",     "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"user": "MatteMoretto",     "name": "Matteo Moretto",     "flag": "🇪🇸"},
    {"user": "Plettigoal",       "name": "Florian Plettenberg","flag": "🇩🇪"},
    {"user": "BenJacobs",        "name": "Ben Jacobs",         "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"user": "Ekremkonur",       "name": "Ekrem Konur",        "flag": "🇹🇷"},
]

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
    "https://nitter.privacydev.net",
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
    "Europa League", "Here we go", "HERE WE GO", "done deal",
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
            import re
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
        # HERE WE GO ni to'g'irlash
        for wrong in ["Mana, ketdik!", "Bu yerga boring!", "Mana boring!", "Keling!", "Mana ket!"]:
            result = result.replace(wrong, "HERE WE GO!")
        return result
    except Exception as e:
        print(f"Tarjima xato: {e}")
        return None

def get_tweets(username):
    for host in NITTER_HOSTS:
        try:
            r = requests.get(f"{host}/{username}", timeout=15, headers=HEADERS)
            if r.status_code != 200:
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
                print(f"OK {host}/{username}: {len(tweets)} post")
                return tweets
        except Exception as e:
            print(f"Xato {host}/{username}: {e}")
    return []

def send(source, original, translated):
    here = "here we go" in original.lower()
    icon = "🟢 <b>HERE WE GO!</b>\n\n" if here else ""

    text = (
        f"⚽ <b>{source['name']}</b> {source['flag']}\n\n"
        f"{icon}"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>"
    )
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        },
        timeout=15
    )
    if r.status_code == 200:
        print(f"Yuborildi [{source['name']}]: {original[:50]}")
        return True
    print(f"Telegram xato: {r.text[:150]}")
    return False

def main():
    global SEEN
    print("=" * 50)
    print(f"Transfer Bot ishga tushdi")
    print(f"Manbalar: {len(SOURCES)} ta insider")
    print(f"Kanal: {CHANNEL_ID}")
    print(f"Har {CHECK_EVERY//60} daqiqada tekshiradi")
    print("=" * 50)

    # Birinchi ishganda barcha mavjud postlarni belgilab qo'y
    for source in SOURCES:
        tweets = get_tweets(source["user"])
        for t in tweets:
            key = f"{source['user']}:{t[:100]}"
            SEEN.add(key)
        print(f"{source['name']}: {len(tweets)} post belgilandi")
        time.sleep(2)

    print("Yangi postlar kutilmoqda...")

    while True:
        time.sleep(CHECK_EVERY)
        print(f"\n[{datetime.now().strftime('%H:%M')}] Tekshirilmoqda...")
        try:
            total_new = 0
            for source in SOURCES:
                tweets = get_tweets(source["user"])
                for tweet in tweets:
                    key = f"{source['user']}:{tweet[:100]}"
                    if key in SEEN:
                        continue
                    tr = translate(tweet)
                    if tr and send(source, tweet, tr):
                        SEEN.add(key)
                        total_new += 1
                        time.sleep(3)
                time.sleep(2)
            print(f"{total_new} ta yangi post yuborildi" if total_new else "Yangi post yoq")
        except Exception as e:
            print(f"Xato: {e}")

if __name__ == "__main__":
    main()
