# dsmlkz_admin_bot

Telegram admin helper for forwarding channel posts, parsing them into structured content, and generating polished job posts (text + image) for re-publication. Built with Aiogram (webhooks) + FastAPI, Supabase for storage, and OpenAI for job description assistance.

## What the bot does
- Forwarded posts: accepts forwarded channel messages, lets you parse them as news or jobs, previews the parsed HTML, and saves the result (plus uploaded image) into Supabase.
- Job generation: `/new_jd` command prompts for IT/ML template, uses OpenAI to extract structured metadata from free-form JD text, renders an image card, and returns Markdown.
- Storage: uploads photos to Supabase storage and saves structured rows into `channels_content` and `job_details`.

## Commands and buttons
- `/new_jd` — generate a job post from raw text (IT/ML templates available).
- Inline buttons after forwarding a post:
  - `📄 Parse as News` / `💼 Parse as Job` — parse and preview.
  - `✅ Yes` / `❌ No` — confirm or cancel saving parsed content.
  - `❌ Cancel` — abort the flow.
  - (`✏️ Generate Job` button exists in UI but is not wired to a handler yet.)

## Architecture (key files)
- FastAPI + webhook bootstrapping: `dsmlkz_admin_bot/run.py` (sets webhook, exposes `/webhook`).
- Bot wiring and handlers: `communication/message_handlers.py`, `communication/new_jd_handler.py`.
- Parsing: `parsing/base_parsing.py`, `parsing/jobs_parsing.py`, `parsing/parsed_message.py`.
- Services: `services/hr_assistant_service.py` (OpenAI JSON-mode parser/Markdown), `services/jd_drawing_service.py` (image card generator).
- Keyboards/UI: `keyboards.py`.
- Config/prompts: `configs/config.py`, `configs/prompts.py`.
- Assets: `assets/images/*` (templates), `assets/fonts/*`.

## Configuration
Set via environment (see `.env` for local):
- `BOT_TOKEN` — Telegram bot token.
- `WEBHOOK_URL` — public HTTPS URL ending with `/webhook` (e.g., `https://your-domain.com/webhook`).
- `SUPABASE_URL`, `SUPABASE_ROLE_KEY` — Supabase project URL and service role key.
- `HR_ASSISTANT_MODEL` — optional, defaults to `gpt-4o-mini`.
- `OPENAI_API_KEY` — OpenAI key for JD parsing/generation.
- Buckets: `SUPABASE_BUCKET` default is `telegram-images`; change in `configs/config.py` if needed.

## Run locally
1) Python 3.11.7 (`runtime.txt`).  
2) Install deps: `pip install -r requirements.txt`.  
3) Set env vars (`BOT_TOKEN`, `WEBHOOK_URL`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ROLE_KEY`, optional `HR_ASSISTANT_MODEL`).  
4) Start API: `uvicorn dsmlkz_admin_bot.run:app --host 0.0.0.0 --port 8000`.  
5) Expose publicly for Telegram (e.g., `ngrok http 8000`) and update `WEBHOOK_URL` accordingly (must end with `/webhook`).  
6) Open Telegram, forward a channel post to the bot and choose an action; or run `/new_jd` and send a JD text.

## Webhook troubleshooting / manual set
- Check current webhook:  
  `curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"`
- Set webhook using your current `.env` values (loads `.env`, then calls Telegram):  
  ```bash
  bash scripts/set_webhook.sh
  ```
- Manually set/reset webhook (replace vars if you don't want to source `.env`):  
  `curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"`
- If you need to set it from Python (with env vars loaded):  
  ```bash
  python3 - <<'PY'
  import os, asyncio
  from aiogram import Bot
  async def main():
      bot = Bot(token=os.environ["BOT_TOKEN"])
      await bot.set_webhook(os.environ["WEBHOOK_URL"])
      info = await bot.get_webhook_info()
      print(info)
      await bot.session.close()
  asyncio.run(main())
  PY
  ```
- Stop webhook (switch to polling or redeploy):  
  `curl "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"`

## File tree (trimmed)
```
dsmlkz_admin_bot/
├─ dsmlkz_admin_bot/
│  ├─ run.py
│  ├─ keyboards.py
│  ├─ communication/
│  │  ├─ message_handlers.py
│  │  ├─ message_processor.py
│  │  └─ new_jd_handler.py
│  ├─ parsing/
│  │  ├─ base_parsing.py
│  │  ├─ jobs_parsing.py
│  │  └─ parsed_message.py
│  ├─ services/
│  │  ├─ hr_assistant_service.py
│  │  └─ jd_drawing_service.py
│  └─ utils/
│     └─ entities_parser.py
├─ configs/
│  ├─ config.py
│  └─ prompts.py
├─ assets/
│  ├─ images/
│  └─ fonts/
├─ scripts/ (helpers: upload_faces.py, process_batch.py)
├─ requirements.txt
├─ Procfile (uvicorn entrypoint)
└─ runtime.txt
```
