# Poputka88 Finland

Отдельный Telegram-бот на базе [poputka88](https://github.com/callumcox819-svg/poputka88) для **Финляндии** (маркетплейс **Tori.fi**).

Скопирован с `poputka88-norway` (Norwa88). Интеграция **Aqua / GOO Network**; HTML-шаблоны в `data/HTMLfi/tori_fi/`.

## Что нужно от тебя

1. **BOT_TOKEN** — новый бот в [@BotFather](https://t.me/BotFather).
2. **ADMIN_IDS** — твой Telegram ID.
3. **VALIDEMAIL_API_KEY** (и при необходимости `_2` … `_5`).
4. **Команды BotFather** — когда будут готовы, вставь в `BOTFATHER_COMMANDS.txt` и выполни:
   ```powershell
   cd C:\Users\user\Desktop\poputka88-finland
   .venv\Scripts\python scripts\set_commands.py
   ```
5. **Aqua / GOO API** — User key + Team key + **profileID** из панели Aqua.
   Домен генерации по умолчанию: `OLD` (`AQUA_GENERATE_DOMAIN=OLD`).
   Сервис: **`tori_fi`** (`AQUA_DEFAULT_SERVICE=tori_fi`).

## Быстрый старт (локально)

```powershell
cd C:\Users\user\Desktop\poputka88-finland
copy config.example.py config_local.py
# отредактируй config_local.py: BOT_TOKEN, ADMIN_IDS, ключи

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

## Домены валидации (по умолчанию)

При первом `/start` подставляется приоритет:

`elisa.fi`, `gmail.com`, `hotmail.com`, `outlook.com`, `yahoo.com`, `icloud.com`, `live.fi`, `me.com`

Изменить: **⚙️ Настройки → 📊 Приоритет отправки**.

## Railway (как norwa88)

**Пошагово:** `RAILWAY_FINLAND.txt`

1. **PostgreSQL** в проекте + `DATABASE_URL` = Reference на оба сервиса.
2. **finland88** (или своё имя) — `python bot.py`, `IMAP_DEDICATED_WORKER=1`.
3. **imap-worker** — `python imap_worker.py`, `ENABLE_INCOMING_MAIL=1`, тот же Postgres и `BOT_TOKEN`.

## Отличия от poputka88-norway

| | poputka88-norway | poputka88-finland |
|---|------------------|-------------------|
| Маркетплейс | Finn.no | **Tori.fi** |
| Aqua service | `finn_no` | **`tori_fi`** |
| HTML | `data/HTMLno/finn_no/` | `data/HTMLfi/tori_fi/` |
| Цена в письмах | kr / NOK | **€ / EUR** |
| IMAP метки | finn.no | **tori.fi** |
| Домены валидации | online.no, … | **elisa.fi**, … |
