# ⚽ Fabrizio Romano Transfer Bot — O'rnatish Qo'llanmasi

## Nima qiladi?
- Fabrizio Romano Twitter/X postlarini avtomatik kuzatadi
- O'zbek tiliga tarjima qiladi (bepul)
- Telegram kanalingizga yuboradi
- Har 10 daqiqada yangi postlarni tekshiradi

---

## 1-qadam: Telegram Bot yaratish

1. Telegramda **@BotFather** ni oching
2. `/newbot` yozing
3. Bot nomini kiriting (masalan: `Romano Transfer Bot`)
4. Username kiriting (masalan: `romano_uz_bot`)
5. Sizga **token** beriladi → saqlab qo'ying!

---

## 2-qadam: Kanalingizga bot qo'shish

1. Telegram kanalingizni oching → Sozlamalar → Adminlar
2. Botingizni admin qiling
3. "Xabar yuborish" ruxsatini bering
4. Kanal ID ni oling:
   - Agar kanal public bo'lsa: `@kanal_nomi`
   - Agar private bo'lsa: [@username_to_id_bot](https://t.me/username_to_id_bot) orqali ID oling

---

## 3-qadam: Railway ga deploy qilish

### 3.1 — GitHub ga yuklash
```bash
git init
git add .
git commit -m "Romano bot"
git remote add origin https://github.com/SIZNING_USERNAME/romano-bot.git
git push -u origin main
```

### 3.2 — Railway.app da sozlash
1. [railway.app](https://railway.app) ga kiring (GitHub bilan)
2. **New Project** → **Deploy from GitHub repo**
3. Romano bot reponi tanlang

### 3.3 — Environment Variables (muhim!)
Railway → Variables bo'limiga quyidagilarni kiriting:

| Kalit | Qiymat | Misol |
|-------|--------|-------|
| `BOT_TOKEN` | BotFather bergan token | `1234567890:AABBcc...` |
| `CHANNEL_ID` | Kanal username yoki ID | `@romano_uz` yoki `-1001234567` |
| `CHECK_EVERY` | Tekshirish oralig'i (soniya) | `600` (10 daqiqa) |

---

## 4-qadam: Ishga tushirish

Railway avtomatik deploy qiladi. Logs bo'limida quyidagini ko'rasiz:
```
🤖 Bot ishga tushdi | Har 10 daqiqada tekshiradi
📡 Kanal: @romano_uz
🔍 [10:30:00] Yangi postlar tekshirilmoqda...
✅ nitter.poast.org dan 8 ta post olindi
```

---

## Muammolar va yechimlari

**Nitter ishlamasa:**
- Bot avtomatik boshqa Nitter serverga o'tadi
- Agar hamma server ishlamasa, bir oz kuting

**"Chat not found" xatosi:**
- Botni kanalga admin qilganingizga ishonch hosil qiling

**Tarjima sifati past:**
- Google Translate bepul, lekin futbol atamalarini ba'zida noto'g'ri tarjima qilishi mumkin
- "Here we go!" → "Mana, ketdik!" deb tarjima bo'lishi normal

---

## Xarajat
| Qism | Narx |
|------|------|
| Railway (oyiga 500 soat bepul) | **Bepul** |
| Google Translate | **Bepul** |
| Telegram Bot API | **Bepul** |
| Nitter | **Bepul** |
| **Jami** | **$0** |
