# 📄 Telegram Challenge Bot

Zamonaviy Telegram bot - har kuni avtomatik xabar yuborish uchun yaratilgan.

## 🔧 Texnologiyalar

| Texnologiya           | Maqsadi                                          |
| --------------------- | ------------------------------------------------ |
| Python                | Asosiy dasturlash tili                           |
| `python-telegram-bot` | Telegram API bilan ishlash (`v20.7`)             |
| `sqlite3`             | Foydalanuvchilar, kanallar va rejalarning bazasi |
| `APScheduler`         | Xabarlarni har kuni belgilangan vaqtda yuborish  |
| `pytz`                | Tashkent vaqt zonasi (`Asia/Tashkent`)           |
| Async/Await           | Asinxron ishlovchi `telegram.ext.Application`    |

## 🚀 O'rnatish va ishga tushirish

### 1. Kerakli kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 2. Bot token olish

1. Telegram'da [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` komandasi bilan yangi bot yarating
3. Bot token'ini nusxalab oling

### 3. Environment variables sozlash

`env_example.txt` faylini `.env` ga o'zgartiring va token'ni kiriting:

```bash
cp env_example.txt .env
```

`.env` faylini ochib, token'ni kiriting:

```
BOT_TOKEN=your_actual_bot_token_here
```

### 4. Botni ishga tushirish

```bash
python bot.py
```

## 🧩 Bot Tuzilishi

| Fayl nomi      | Tavsif                                                            |
| -------------- | ----------------------------------------------------------------- |
| `bot.py`       | Asosiy fayl, komandalar, holatlar, va foydalanuvchi bilan muloqot |
| `db.py`        | SQLite bazasi bilan ishlash: foydalanuvchilar, kanallar, rejalar  |
| `scheduler.py` | APScheduler yordamida xabarlarni har kuni yuborish                |
| `config.py`    | Bot konfiguratsiyasi va sozlamalar                                |

## 👤 Foydalanuvchi Uchun Imkoniyatlar

### 1. `/start` — Bot haqida ma'lumot

- Foydalanuvchini kutib oladi
- Bot imkoniyatlarini tushuntiradi
- Adminga murojaat uchun username beradi (`@shamsiyev1909`)

### 2. `/kanal_ulash` — Kanal ulash

- Foydalanuvchi kanal `@username` yoki `-100...` ID sini yuboradi
- Bot kanalni tekshiradi:
  - Kanal mavjudmi
  - Bot adminmi (xabar yuborish ruxsatiga egami)
- Muvaffaqiyatli ulangan kanal bazaga saqlanadi

### 3. `/kanallarim` — Ulangan kanallar ro'yxati

- Foydalanuvchining barcha bog'langan kanallari ko'rsatiladi
- Format: `Kanal nomi (ID)`

### 4. `/send` — Xabar rejalashtirish

**Xabar yuborish bosqichlari:**

1. Foydalanuvchi kanalni tanlaydi
2. Bot xabar matnini so'raydi
3. Soat nechada yuborilishini so'raydi (format: `HH:MM`)
4. Sana va "challenge kuni" qo'shilsinmi deb so'raydi

**So'ng:**

- Reja `schedules` jadvaliga yoziladi
- Har kuni belgilangan vaqtda APScheduler orqali xabar yuboriladi

### 5. `/rejalarim` — Rejalashtirilgan xabarlar

- Foydalanuvchiga u rejalashtirgan barcha xabarlar ko'rsatiladi:
  - Kanal
  - Xabar matni
  - Har kuni yuboriladigan soat
  - Sana va "challenge kuni" qo'shilganmi yoki yo'q
  - Qo'shilgan sanasi

## 📦 Ma'lumotlar Bazasi Strukturasi (SQLite)

### `users`

Foydalanuvchilar ro'yxati.

| Field    | Type    | Tavsif             |
| -------- | ------- | ------------------ |
| user_id  | INTEGER | Telegram user ID   |
| username | TEXT    | Telegram @username |

### `channels`

Har bir foydalanuvchining ulagan kanallari.

| Field        | Type    | Tavsif           |
| ------------ | ------- | ---------------- |
| id           | INTEGER | Avto inkrement   |
| user_id      | INTEGER | Foydalanuvchi ID |
| channel_id   | TEXT    | Kanal ID         |
| channel_name | TEXT    | Kanal nomi       |

### `schedules`

Har kuni yuboriladigan xabarlar.

| Field      | Type    | Tavsif                                  |
| ---------- | ------- | --------------------------------------- |
| id         | INTEGER | Rejaning ID                             |
| user_id    | INTEGER | Reja egasi                              |
| channel_id | TEXT    | Qaysi kanalga yuboriladi                |
| message    | TEXT    | Yuboriladigan xabar                     |
| time       | TEXT    | Har kuni yuboriladigan vaqt (`HH:MM`)   |
| with_date  | INTEGER | Sana va challenge kuni yozilsinmi (0/1) |
| start_date | TEXT    | Reja boshlang'an sana (`YYYY-MM-DD`)    |
| day_count  | INTEGER | Challenge kuni (boshlanishi 1 dan)      |

## 🕑 APScheduler: Avtomatik Xabar Yuborish

- Har kuni kerakli vaqtda ishga tushadigan **cron jobs**lar qo'shiladi
- Har bir job `job_id=f"userID_channelID_soat"` formatida nomlanadi
- `with_date=1` bo'lsa:
  - Sana avtomatik qo'shiladi
  - `day_count` yangilanadi

**Xabar formati:**

```
📅 2025-07-08 — Challenge kuni: 3
Xabar matni...
```

## 💥 Muammolar Yechimi

| Muammo                                      | Yechim                                                 |
| ------------------------------------------- | ------------------------------------------------------ |
| `ModuleNotFoundError: No module 'telegram'` | Virtual muhit (venv310) aktivlashtirilmagan edi        |
| `f-string` syntax xatosi                    | `\'` belgisini f-string ichida ishlatish xatolik berdi |
| APScheduler xatoliklari                     | Har bir job `id` bilan unikal qilindi                  |

## 📌 Xulosa

Sizning **Telegram Challenge Bot**ingiz quyidagilarni amalga oshiradi:

✅ Har kuni **avtomatik xabar yuboradi**
✅ Xabarlar **kanallarga rejalashtirib** yuboriladi
✅ **Kanal ulash**, **xabar rejalash**, **ro'yxat ko'rish** komandalar mavjud
✅ Har bir foydalanuvchi o'ziga xos **kanallar va rejalar** saqlaydi
✅ Sana va **"challenge kuni"** avtomatik hisoblanadi
✅ Bot **modular va asinxron** ishlaydi — zamonaviy arxitektura asosida

## 🤝 Yordam

Agar savollar bo'lsa: [@shamsiyev1909](https://t.me/shamsiyev1909)
