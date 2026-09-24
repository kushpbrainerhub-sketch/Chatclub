# Chatclub — random stranger text chat

Free, anonymous, text-only chat. Male ↔ Female random matching with mutual age/country filters.
No accounts, no database — everything lives in memory and disappears when a chat ends.
Full requirements are in [SPEC.md](SPEC.md).

```
backend/    FastAPI + WebSocket server (Python)
  main.py       /health and /ws, rate limits, reports, online count
  matcher.py    waiting queue + compatibility check (no WebSocket code, easy to test)
  models.py     validation rules (age 18-99, username, country, filters)
  countries.py  valid country codes
  filters.py    simple bad-word filter
  tests/        pytest tests
frontend/   React + Vite
  src/useChatSocket.js     all WebSocket logic
  src/components/          ProfileForm, WaitingScreen, ChatRoom
```

## Run it on your computer (Windows)

**Terminal 1 — backend**

```powershell
cd backend
python -m venv venv          # only the first time
venv\Scripts\activate
pip install -r requirements.txt   # only the first time
uvicorn main:app --reload --port 8000
```

Check it: open http://localhost:8000/health → `{"status":"ok"}`

**Terminal 2 — frontend**

```powershell
cd frontend
npm install                  # only the first time
copy .env.example .env       # only the first time
npm run dev
```

Open http://localhost:5173 in a normal window **and** an incognito window.
Make one Male and one Female → they get matched.

> On macOS/Linux use `source venv/bin/activate` and `cp .env.example .env`.

## Run the tests

```powershell
cd backend
venv\Scripts\activate
pytest
```

`test_matcher.py` covers the matching rules, `test_websocket.py` runs real two-user chats against `/ws`.

## Deploy

### Backend → Render (Web Service)

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Env var `PYTHON_VERSION` | `3.12.7` (any 3.11+) |
| Env var `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (comma-separate several) |

Important: run **one instance only**. The queue is in memory, so two servers would have two separate queues
(Redis is the fix for that later — see SPEC "Future ideas"). Render's free plan sleeps when idle,
so the first visit after a while takes ~30-60 seconds to wake up.

### Frontend → Vercel

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite |
| Env var `VITE_WS_URL` | `wss://your-backend.onrender.com/ws` |

Note `wss://` (secure) in production, not `ws://`. After changing an env var on Vercel, redeploy.

## Rules the server enforces

- Age 18-99, gender male/female, valid country, username 3-20 chars (`a-z 0-9 _ .` and space)
- Male only matches Female; age and country filters must fit **both ways**
- "Next" won't re-pair you with the person you just left ("Stop" clears this)
- Max 5 messages/second, max 10 "Next" per minute, messages 1-1000 characters
- 3 reports (from different people) in one session → disconnected; reports are printed to the backend console
- Blocked words in `backend/filters.py` are replaced with `***`
