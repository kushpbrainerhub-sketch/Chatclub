# 💬 Chatclub — free anonymous chat with random strangers

**Live site: https://chatclub-app.vercel.app**

Chatclub pairs you with a random stranger for a private, text-only chat.
No signup, no login, no payments, and nothing is saved: when a chat ends, the messages are gone.
The original requirements are in [SPEC.md](SPEC.md).

---

## Features

- **Instant random matching**: Male ↔ Female, with optional **country** (multi-select) and **age range** filters.
  Filters must fit **both ways** before two people are matched.
- **Real-time chat** over WebSockets: messages, "Stranger is typing...", online user count.
- **Next / Stop / Report** buttons. Next never re-pairs you with the person you just skipped.
- **Safety**: 18+ only (checked on frontend and backend), rate limits, bad-word filter,
  auto-disconnect after 3 reports, HTML-safe message rendering.
- **Privacy**: no accounts, no database, no cookies, no trackers.
- **Mobile friendly**, automatic light/dark theme.
- **SEO ready**: meta tags, link-preview image, sitemap, robots.txt, About/FAQ with FAQ structured data,
  Privacy Policy and Terms pages, registered in Google Search Console.

## Live links

| What | URL | Hosted on (free) |
|---|---|---|
| Website | https://chatclub-app.vercel.app | Vercel |
| About & FAQ | https://chatclub-app.vercel.app/about | Vercel |
| Privacy / Terms | [/privacy](https://chatclub-app.vercel.app/privacy) · [/terms](https://chatclub-app.vercel.app/terms) | Vercel |
| Chat server | https://chatclub-backend-huq4.onrender.com/health | Render |
| Code | https://github.com/kushpbrainerhub-sketch/Chatclub | GitHub |

The old address `chatclub-rouge.vercel.app` permanently redirects (308) to the new one.

---

## How it works

```
 Browser (React)                      Server (FastAPI)
┌──────────────────┐   WebSocket    ┌─────────────────────────────┐
│ ProfileForm      │ ─── join ────▶ │ validate (models.py)        │
│ WaitingScreen    │ ◀── waiting ── │ matcher.py: FIFO queue,     │
│ ChatRoom         │ ◀── matched ── │   is_compatible() both ways │
│                  │ ─── message ─▶ │ forward to partner only     │
│ useChatSocket.js │ ◀── message ── │ (nothing stored)            │
└──────────────────┘                └─────────────────────────────┘
```

1. The browser opens one WebSocket to `/ws` and sends `join` with the profile and filters.
2. The server checks everything again (it never trusts the browser), then looks through the waiting
   list, oldest first, for someone compatible **in both directions**. If nobody fits, you wait.
3. Messages go straight to your partner. When either person leaves, disconnects or presses Next,
   the other gets `partner_left`.

The full list of events is in [SPEC.md §6](SPEC.md).

## Project structure

```
backend/                 FastAPI + WebSocket server (Python)
  main.py                  /health, /ws, rate limits, reports, online count
  matcher.py               waiting queue + compatibility check (no WebSocket code → easy to test)
  models.py                validation rules (age 18-99, username, country, filters, message length)
  countries.py             valid country codes (same list as frontend/src/countries.js)
  filters.py               bad-word filter (edit BLOCKED_WORDS)
  tests/                   27 pytest tests (matcher rules + real two-user WebSocket chats)
frontend/                React + Vite
  src/useChatSocket.js     all WebSocket logic (connect, reconnect once, send, state)
  src/components/          ProfileForm, WaitingScreen, ChatRoom
  public/                  about/privacy/terms pages, robots.txt, sitemap.xml, icons, share image
  index.html               SEO + link-preview tags
  vercel.json              short URLs (/about → about.html)
render.yaml              how Render runs the backend
.github/workflows/       keep-alive: pings the backend every 10 min so it never sleeps
```

---

## Run it on your computer (Windows)

**Terminal 1: backend**

```powershell
cd backend
python -m venv venv                 # first time only
venv\Scripts\activate
pip install -r requirements.txt     # first time only
uvicorn main:app --reload --port 8000
```

Check: http://localhost:8000/health → `{"status":"ok"}`

**Terminal 2: frontend**

```powershell
cd frontend
npm install                  # first time only
copy .env.example .env       # first time only
npm run dev
```

Open http://localhost:5173 in a normal window **and** an incognito window, make one Male and one Female,
and they get matched.

> `WinError 10013` when starting the backend means port 8000 is already used by another server.
> Close the other terminal, or use `--port 8001` and set `VITE_WS_URL=ws://localhost:8001/ws` in `frontend/.env`.
> On macOS/Linux use `source venv/bin/activate` and `cp .env.example .env`.

## Tests

```powershell
cd backend
venv\Scripts\activate
pytest
```

---

## Deployment (already set up)

Every `git push` to `main` redeploys automatically:

- **Vercel** builds `frontend/` (preset Vite).
  Environment variable: `VITE_WS_URL=wss://chatclub-backend-huq4.onrender.com/ws`
- **Render** runs `backend/` using [render.yaml](render.yaml)
  (`uvicorn main:app --host 0.0.0.0 --port $PORT`, free plan).
  `ALLOWED_ORIGINS` is set in `render.yaml`. After changing it, open the Blueprint in Render and click **Manual sync** → **Approve**.
- **GitHub Actions** ([keep-alive.yml](.github/workflows/keep-alive.yml)) pings `/health` every 10 minutes
  so Render's free server doesn't fall asleep. GitHub pauses scheduled jobs after 60 days with no commits,
  so re-enable it from the **Actions** tab if that happens.

Run **one** backend instance only: the matching queue lives in memory. Running several servers needs
Redis (see SPEC "Future ideas").

## Google / SEO

- The site is verified in **Google Search Console** (HTML file `frontend/public/google8c1d6245f72f486f.html`;
  **don't delete it** or verification is lost) and `sitemap.xml` is submitted.
- Google usually lists a new site within a few days to 2 weeks. Check progress in Search Console → **Pages**.
- If you add or rename pages, update `frontend/public/sitemap.xml`.
- If you move to your own domain, replace `chatclub-app.vercel.app` in `index.html`, the pages in `public/`,
  `robots.txt`, `sitemap.xml` and `render.yaml`, then add the new domain in Search Console.

### Getting more visitors

Showing up on Google is not the same as ranking #1. Words like "random chat" are very competitive.
What actually helps:

1. **Share the link** on Reddit, Instagram, WhatsApp groups, Discord and X. The link preview image is ready.
2. **Get other sites to link to you**: list Chatclub on free directories (Product Hunt, AlternativeTo, "Omegle alternatives" lists).
3. **Own domain**: a short `.com`/`.in` (about ₹500–1,000/year) looks more trustworthy and helps ranking.
4. **Keep adding useful content** (safety tips, chat ideas) to the About page or new pages.

---

## Rules the server enforces

| Rule | Limit |
|---|---|
| Age | 18–99 (profile and filters), min ≤ max |
| Gender | `male` or `female`; male only matches female |
| Username | 3–20 characters: letters, numbers, `_`, `.`, space |
| Country | valid ISO code from `countries.py` |
| Message | 1–1000 characters, bad words replaced with `***` |
| Rate limits | 5 messages/second, 10 "Next" per minute |
| Reports | 3 reports from different people → disconnected (logged to the Render console) |
