# Attention Seeker

Triggers a **real phone call** to your number so your phone’s actual ringtone and system call UI take over.

Browsers cannot invent a cellular ring by themselves. This app uses [Twilio](https://www.twilio.com) to call you for real.

## Toxic / loud ringtone

Set **Toxic** (or anything else) as your **system ringtone** in iPhone/Android Settings. When the real call arrives, that ringtone plays at your normal ringtone volume.

## Setup

1. Create a free Twilio account and get a phone number.
2. Copy env file and fill in credentials:

```bash
copy .env.example .env
```

3. Start the real-call server (not a plain static server):

```bash
py server.py
```

4. Open `http://127.0.0.1:5173`
5. Enter your number as `+91…` / `+1…`, pick a delay, tap **RING**

### Trial accounts

Twilio trial numbers can usually only call **verified** destination numbers. Verify your phone in the Twilio console first.

## How it works

1. You tap RING (optional countdown)
2. Server asks Twilio to call **your** phone
3. Your phone rings like any normal incoming call
4. Accept / decline as usual

## API

- `GET /api/health` — server + Twilio config status  
- `POST /api/call` — `{ "to": "+15551234567" }` places the call
