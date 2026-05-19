import os
import re
import json
import time
import requests

from datetime import datetime
from bs4 import BeautifulSoup

# ==========================================
# CONFIG
# ==========================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

CHECK_EVERY = int(
    os.environ.get("CHECK_EVERY", "300")
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
]

SEEN = set()

# ==========================================
# KEEP WORDS
# ==========================================

KEEP_WORDS = [
    "Real Madrid",
    "Barcelona",
    "Manchester United",
    "Manchester City",
    "Liverpool",
    "Chelsea",
    "Arsenal",
    "Tottenham",
    "Bayern Munich",
    "PSG",
    "Juventus",
    "AC Milan",
    "Inter Milan",
    "Napoli",
    "Atletico Madrid",
    "Borussia Dortmund",
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Champions League",
    "Europa League",
    "HERE WE GO",
    "Here we go",
]

# ==========================================
# TRANSLATE
# ==========================================

def protect_words(text):

    placeholders = {}

    for i, word in enumerate(KEEP_WORDS):

        if word.lower() in text.lower():

            placeholder = f"XXWORD{i}XX"

            placeholders[placeholder] = word

            text = re.sub(
                re.escape(word),
                placeholder,
                text,
                flags=re.IGNORECASE
            )

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
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "uz",
                "dt": "t",
                "q": protected
            },
            timeout=20
        )

        translated = "".join(
            x[0] for x in r.json()[0] if x[0]
        )

        translated = restore_words(
            translated,
            placeholders
        )

        bad_words = [
            "Mana, ketdik!",
            "Mana boring!",
            "Bu yerga boring!",
            "Keling!",
            "Mana ket!",
            "Mana keting!"
        ]

        for bad in bad_words:
            translated = translated.replace(
                bad,
                "HERE WE GO!"
            )

        return translated

    except Exception as e:

        print("TRANSLATE ERROR:", e)

        return text


# ==========================================
# GET MEDIA
# ==========================================

def get_images_from_nitter(item, host):

    images = []

    media = item.select(".attachments img")

    for img in media:

        src = img.get("src", "")

        if not src:
            continue

        # relative url
        if src.startswith("/"):
            src = host + src

        # original quality
        src = src.replace("/pic/", "/pic/orig/")

        # skip profile photos
        if "profile_images" in src:
            continue

        images.append(src)

    # remove duplicates
    return list(dict.fromkeys(images))


def get_video_from_nitter(item, host):

    try:

        video = item.select_one("video source")

        if not video:
            return None

        src = video.get("src")

        if not src:
            return None

        if src.startswith("/"):
            src = host + src

        return src

    except:
        return None


# ==========================================
# TWEET LINK
# ==========================================

def get_tweet_link(item):

    try:

        link = item.select_one("a.tweet-link")

        if not link:
            return "https://twitter.com/FabrizioRomano"

        href = link.get("href", "")

        if href.startswith("/"):
            return "https://twitter.com" + href

        return href

    except:
        return "https://twitter.com/FabrizioRomano"


# ==========================================
# GET POSTS
# ==========================================

def get_tweets():

    for host in NITTER_HOSTS:

        try:

            print(f"CHECKING {host}")

            r = requests.get(
                f"{host}/FabrizioRomano",
                headers=HEADERS,
                timeout=20
            )

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(
                r.text,
                "html.parser"
            )

            tweets = []

            items = soup.select(".timeline-item")

            for item in items:

                # skip retweets
                if item.select_one(".retweet-header"):
                    continue

                content = item.select_one(
                    ".tweet-content"
                )

                if not content:
                    continue

                text = content.get_text(
                    " "
                ).strip()

                if len(text) < 15:
                    continue

                images = get_images_from_nitter(
                    item,
                    host
                )

                video = get_video_from_nitter(
                    item,
                    host
                )

                link = get_tweet_link(item)

                tweets.append({
                    "text": text,
                    "images": images,
                    "video": video,
                    "link": link
                })

            if tweets:

                print(
                    f"OK {host} | "
                    f"{len(tweets)} POSTS"
                )

                return tweets

        except Exception as e:

            print("SCRAPE ERROR:", e)

    return []


# ==========================================
# DOWNLOAD FILE
# ==========================================

def download_file(url):

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        if r.status_code == 200:
            return r.content

    except Exception as e:

        print("DOWNLOAD ERROR:", e)

    return None


# ==========================================
# CAPTION
# ==========================================

def build_caption(original, translated):

    here = "here we go" in original.lower()

    icon = ""

    if here:
        icon = "🟢 <b>HERE WE GO!</b>\n\n"

    caption = (
        f"⚽ <b>Fabrizio Romano</b> 🇮🇹\n\n"
        f"{icon}"
        f"🇺🇿 {translated}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇬🇧 <i>{original}</i>"
    )

    return caption


# ==========================================
# SEND MEDIA GROUP
# ==========================================

def send_media_group(images, caption):

    media = []
    files = {}

    for i, img_url in enumerate(images[:10]):

        print("DOWNLOADING:", img_url)

        img_data = download_file(img_url)

        if not img_data:
            continue

        filename = f"photo{i}.jpg"

        files[filename] = (
            filename,
            img_data,
            "image/jpeg"
        )

        item = {
            "type": "photo",
            "media": f"attach://{filename}"
        }

        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"

        media.append(item)

    if not media:

        print("NO MEDIA")

        return False

    try:

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
            data={
                "chat_id": CHANNEL_ID,
                "media": json.dumps(media)
            },
            files=files,
            timeout=60
        )

        print("MEDIA RESPONSE:")
        print(r.text)

        return r.status_code == 200

    except Exception as e:

        print("MEDIA SEND ERROR:", e)

        return False


# ==========================================
# SEND VIDEO
# ==========================================

def send_video(video_url, caption):

    try:

        print("DOWNLOADING VIDEO")

        video_data = download_file(video_url)

        if not video_data:
            return False

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
            data={
                "chat_id": CHANNEL_ID,
                "caption": caption,
                "parse_mode": "HTML"
            },
            files={
                "video": (
                    "video.mp4",
                    video_data,
                    "video/mp4"
                )
            },
            timeout=120
        )

        print("VIDEO RESPONSE:")
        print(r.text)

        return r.status_code == 200

    except Exception as e:

        print("VIDEO ERROR:", e)

        return False


# ==========================================
# SEND TEXT
# ==========================================

def send_text(caption):

    try:

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=30
        )

        print("TEXT RESPONSE:")
        print(r.text)

        return r.status_code == 200

    except Exception as e:

        print("TEXT ERROR:", e)

        return False


# ==========================================
# SEND POST
# ==========================================

def send_post(original, translated, images, video):

    caption = build_caption(
        original,
        translated
    )

    # video first
    if video:

        print("VIDEO FOUND")

        if send_video(video, caption):
            return True

    # images
    if images:

        print(f"{len(images)} IMAGES FOUND")

        if send_media_group(images, caption):
            return True

    # fallback text
    return send_text(caption)


# ==========================================
# MAIN
# ==========================================

def main():

    global SEEN

    print("=" * 50)
    print("FABRIZIO ROMANO BOT")
    print("=" * 50)

    # first load
    tweets = get_tweets()

    for tweet in tweets:

        key = tweet["text"][:120]

        SEEN.add(key)

    print(f"{len(SEEN)} OLD POSTS SAVED")

    while True:

        try:

            print(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] CHECKING..."
            )

            tweets = get_tweets()

            sent = 0

            for tweet in reversed(tweets):

                key = tweet["text"][:120]

                if key in SEEN:
                    continue

                print("\nNEW POST:")
                print(tweet["text"][:100])

                translated = translate(
                    tweet["text"]
                )

                ok = send_post(
                    tweet["text"],
                    translated,
                    tweet["images"],
                    tweet["video"]
                )

                if ok:

                    SEEN.add(key)

                    sent += 1

                    print("SENT SUCCESS")

                else:

                    print("SEND FAILED")

                time.sleep(5)

            print(f"SENT: {sent}")

        except Exception as e:

            print("MAIN ERROR:", e)

        time.sleep(CHECK_EVERY)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    main()
