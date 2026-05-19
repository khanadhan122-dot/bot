import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re

BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-100XXXXXXXXXX")
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "300"))

SEEN = set()

NITTER_HOSTS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.tiekoetter.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

KEEP_WORDS = [
    "Real Madrid", "Barcelona", "Manchester United",
    "Manchester City", "Liverpool", "Chelsea",
    "Arsenal", "Tottenham", "Bayern Munich",
    "PSG", "Juventus", "AC Milan",
    "Inter Milan", "Napoli", "Atletico Madrid",
    "Borussia Dortmund", "Premier League",
    "La Liga", "Serie A", "Bundesliga",
    "Champions League", "Europa League",
    "HERE WE GO", "Here we go",
]

# =========================================
# TEXT FUNCTIONS
# =========================================

def protect_words(text):
    placeholders = {}

    for i, word in enumerate(KEEP_WORDS):
        if word.lower() in text.lower():
            ph = f"XXWORD{i}XX"
            placeholders[ph] = word

            text = re.sub(
                re.escape(word),
                ph,
                text,
                flags=re.IGNORECASE
            )

    return text, placeholders


def restore_words(text, placeholders):
    for ph, word in placeholders.items():
        text = text.replace(ph, word)

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

        for w in bad_words:
            translated = translated.replace(
                w,
                "HERE WE GO!"
            )

        return translated

    except Exception as e:
        print("Tarjima xato:", e)
        return text


# =========================================
# SCRAPE FUNCTIONS
# =========================================

def get_images_from_nitter(item, host):
    """
    Tweet ichidagi REAL rasmlarni olish
    """

    images = []

    # attachments ichidagi rasmlar
    media = item.select(".attachments img")

    for img in media:

        src = img.get("src", "")

        if not src:
            continue

        # relative url
        if src.startswith("/"):
            src = host + src

        # original size
        src = src.replace("/pic/", "/pic/orig/")

        # profile rasmni skip
        if "profile_images" in src:
            continue

        images.append(src)

    # duplicate remove
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


def get_tweets():

    for host in NITTER_HOSTS:

        try:

            print(f"Checking {host}")

            r = requests.get(
                f"{host}/FabrizioRomano",
                headers=HEADERS,
                timeout=20
            )

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            tweets = []

            items = soup.select(".timeline-item")

            for item in items:

                # retweet skip
                if item.select_one(".retweet-header"):
                    continue

                content = item.select_one(".tweet-content")

                if not content:
                    continue

                text = content.get_text(" ").strip()

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
                    f"{len(tweets)} posts"
                )

                return tweets

        except Exception as e:
            print(host, e)

    return []


# =========================================
# DOWNLOAD
# =========================================

def download_file(url):

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        ctype = r.headers.get(
            "content-type",
            ""
        )

        if r.status_code == 200:
            return r.content, ctype

    except Exception as e:
        print("Download error:", e)

    return None, None


# =========================================
# TELEGRAM SEND
# =========================================

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


def send_media_group(images, caption):

    media = []
    files = {}

    for i, img_url in enumerate(images[:10]):

        img_data, ctype = download_file(img_url)

        if not img_data:
            continue

        file_name = f"photo{i}.jpg"

        files[file_name] = (
            file_name,
            img_data,
            "image/jpeg"
        )

        item = {
            "type": "photo",
            "media": f"attach://{file_name}"
        }

        if i == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"

        media.append(item)

    if not media:
        return False

    try:

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
            data={
                "chat_id": CHANNEL_ID,
                "media": str(media).replace("'", '"')
            },
            files=files,
            timeout=60
        )

        print(r.text)

        return r.status_code == 200

    except Exception as e:
        print("MediaGroup error:", e)
        return False


def send_video(video_url, caption):

    try:

        video_data, ctype = download_file(video_url)

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

        print(r.text)

        return r.status_code == 200

    except Exception as e:
        print("Video error:", e)
        return False


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

        print(r.text)

        return r.status_code == 200

    except Exception as e:
        print("Text error:", e)
        return False


def send_post(original, translated, images, video):

    caption = build_caption(
        original,
        translated
    )

    # video first
    if video:

        print("Video found")

        if send_video(video, caption):
            return True

    # images
    if images:

        print(f"{len(images)} images found")

        if send_media_group(images, caption):
            return True

    # fallback text
    return send_text(caption)


# =========================================
# MAIN
# =========================================

def main():

    global SEEN

    print("=" * 50)
    print("FABRIZIO ROMANO BOT")
    print("=" * 50)

    # first load
    tweets = get_tweets()

    for t in tweets:
        SEEN.add(t["text"][:120])

    print(f"{len(SEEN)} old posts saved")

    while True:

        try:

            print(
                f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking..."
            )

            tweets = get_tweets()

            sent = 0

            for tweet in reversed(tweets):

                key = tweet["text"][:120]

                if key in SEEN:
                    continue

                print("NEW POST:")
                print(tweet["text"][:80])

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

                time.sleep(5)

            print(f"Sent: {sent}")

        except Exception as e:
            print("MAIN ERROR:", e)

        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
