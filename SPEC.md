# Project Spec: Random Stranger Text Chat Web App

> **For Claude Code:** Read this whole file first. Build the project phase by phase (see "Build Order" at the bottom). After each phase, run it, test it, and tell me what works before moving on. Keep the code simple and well commented, I am a beginner.

---

## 1. What we are building

A free, global, text-only chat website where strangers get randomly paired and chat in real time.

- No signup, no login, no password, no subscription, no payments.
- User fills a small profile (username, age, country, gender), sets optional filters, clicks **Start**, and gets matched with a stranger.
- Matching rule: **Male only matches with Female, Female only matches with Male.**
- Text messages only. No images, voice, video, or files.
- Nothing is saved to a database. When a chat ends, the messages are gone.

---

## 2. Tech stack

| Part | Choice |
|---|---|
| Frontend | React (created with Vite), JavaScript, plain CSS or Tailwind |
| Realtime | Browser native `WebSocket` API (no socket.io) |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Storage | In-memory Python data structures only (no database in v1) |
| Hosting (later) | Frontend on Vercel, backend on Render |

---

## 3. Folder structure

```
random-chat/
├── SPEC.md
├── backend/
│   ├── main.py            # FastAPI app + WebSocket route
│   ├── matcher.py         # Queue + matching algorithm
│   ├── models.py          # Pydantic models for profile/filters/messages
│   ├── countries.py       # List of valid country codes
│   ├── requirements.txt
│   └── tests/
│       └── test_matcher.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── .env.example       # VITE_WS_URL=ws://localhost:8000/ws
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── useChatSocket.js   # custom hook for all WebSocket logic
        ├── countries.js       # same country list as backend
        └── components/
            ├── ProfileForm.jsx
            ├── WaitingScreen.jsx
            └── ChatRoom.jsx
```

---

## 4. User flow

1. **Profile screen**
   - Username (text)
   - Age (number)
   - Country (dropdown)
   - Gender (only two options: Male / Female)
   - Checkbox: "I confirm I am 18 or older and agree to be respectful"
2. **Filters (on the same screen, optional)**
   - Partner country: "Any country" (default) or pick one or more countries
   - Partner age range: min and max (default 18 to 99)
   - Partner gender: not shown as a choice, it is automatically the opposite gender. Show a small note like "You'll be matched with: Female".
3. User clicks **Start Chatting** → Waiting screen ("Looking for someone...").
4. When matched → Chat screen shows partner's username, age, country (not gender needed, but can show it).
5. Chat screen buttons:
   - **Send** (also Enter key)
   - **Next** → leave this chat and search again with same profile + filters
   - **Stop** → leave chat and go back to profile screen
   - **Report** → report the partner (see Safety section)
6. If partner leaves → show "Stranger has disconnected" and a button "Find new stranger".
7. The profile and filters should be remembered in React state during the session so user does not retype them on "Next".

---

## 5. Validation rules (check on BOTH frontend and backend)

| Field | Rule |
|---|---|
| username | 3 to 20 characters, letters, numbers, underscore, dot, space. Trim spaces. Does not need to be unique. |
| age | Whole number, **18 to 99**. Reject anything under 18. |
| country | Must be a valid code from the countries list (ISO 3166 alpha-2, e.g. "IN", "US") |
| gender | Exactly `"male"` or `"female"` |
| filter_countries | Array of valid codes. Empty array = any country. |
| filter_age_min / filter_age_max | Both between 18 and 99, and min ≤ max |
| message text | 1 to 1000 characters after trimming |

Backend must never trust the frontend. If validation fails, send an `error` event and do not add the user to the queue.

---

## 6. WebSocket protocol

One endpoint: `GET /ws` (WebSocket). All messages are JSON with a `type` field.

### Client → Server

```json
{ "type": "join", "profile": { "username": "Kush", "age": 22, "country": "IN", "gender": "male" },
  "filters": { "countries": ["IN", "US"], "age_min": 18, "age_max": 30 } }

{ "type": "message", "text": "hello!" }

{ "type": "typing" }

{ "type": "next" }       // leave current chat and re-join queue with same profile/filters

{ "type": "leave" }      // leave chat and queue completely

{ "type": "report", "reason": "spam" }
```

### Server → Client

```json
{ "type": "waiting" }

{ "type": "matched", "partner": { "username": "Riya", "age": 21, "country": "IN" } }

{ "type": "message", "text": "hi!", "from": "partner" }

{ "type": "partner_typing" }

{ "type": "partner_left" }

{ "type": "online_count", "count": 42 }

{ "type": "error", "message": "Age must be between 18 and 99" }
```

---

## 7. Matching algorithm (most important part)

### Data kept in memory (backend)

- `waiting`: an ordered list (FIFO) of users waiting to be matched. Each entry holds: connection id, websocket, profile, filters, time they joined.
- `pairs`: dictionary `{connection_id: partner_connection_id}` (store both directions).
- `connections`: dictionary of all connected users.

### Compatibility check

Two users **A** and **B** are compatible only if ALL of these are true:

1. `A.gender != B.gender` (male ↔ female only)
2. `B.age` is inside A's age range AND `A.age` is inside B's age range
3. A's country filter is empty OR contains `B.country`
4. B's country filter is empty OR contains `A.country`
5. A and B are not the same connection
6. (Nice to have) A and B were not just paired in their previous chat, so "Next" does not reconnect the same two people immediately

Filters must match **both ways** (mutual). Example: A wants age 18-25 and B is 30 → no match, even if B's filters accept A.

### Pseudocode

```python
def is_compatible(a, b):
    if a.id == b.id: return False
    if a.profile.gender == b.profile.gender: return False
    if not (a.filters.age_min <= b.profile.age <= a.filters.age_max): return False
    if not (b.filters.age_min <= a.profile.age <= b.filters.age_max): return False
    if a.filters.countries and b.profile.country not in a.filters.countries: return False
    if b.filters.countries and a.profile.country not in b.filters.countries: return False
    if a.last_partner_id == b.id or b.last_partner_id == a.id: return False
    return True

async def on_join(user):
    for candidate in waiting:          # oldest first = fair
        if is_compatible(user, candidate):
            waiting.remove(candidate)
            pair(user, candidate)      # update pairs dict, send "matched" to both
            return
    waiting.append(user)
    send(user, {"type": "waiting"})
```

### Rules

- Use an `asyncio.Lock` around queue changes so two users cannot grab the same partner at the same time.
- Put the matching logic in `matcher.py` as plain functions/class so it can be unit tested without WebSockets.
- If a user waits more than 30 seconds, the frontend shows a hint: "No match yet. Try widening your age range or country filter." (The user keeps waiting, we do not auto-change filters.)

---

## 8. Disconnect handling

- If a user closes the tab or loses internet: remove them from `waiting`, `connections`, and `pairs`. If they had a partner, send `partner_left` to the partner.
- `next`: end current pair (partner gets `partner_left`), then run `on_join` again with the same profile and filters.
- `leave`: end current pair and remove from queue, keep socket open or close it.
- Always use `try/finally` in the WebSocket loop so cleanup runs no matter how the connection ends.

---

## 9. Safety basics (keep these, they are light)

1. **18+ only**: age field minimum 18 on frontend and backend, plus the confirmation checkbox.
2. **Report button**: backend counts reports per connection. If a user gets 3 reports in one session, disconnect them with an error message. Log reports to the console (no database yet).
3. **Rate limit**: max 5 messages per second and max 10 "next" per minute per connection. Extra messages are dropped with an `error` event.
4. **No HTML injection**: React escapes text by default. Never use `dangerouslySetInnerHTML` for chat messages.
5. **Message length** max 1000 characters.
6. **Simple word filter** (optional, v1.1): a small list of blocked words in `backend/filters.py` that gets replaced with `***`.
7. Show a short line on the home page: "Be respectful. Don't share personal info like phone number or address."

---

## 10. Frontend details

- `useChatSocket.js` custom hook handles: connecting, reconnecting once if dropped, sending JSON, and exposing `status` (`idle | waiting | chatting | partner_left`), `messages`, `partner`, `onlineCount`, `partnerTyping`.
- WebSocket URL comes from `import.meta.env.VITE_WS_URL`.
- Chat UI:
  - My messages on the right, partner's on the left, different colors.
  - Auto-scroll to latest message.
  - "Stranger is typing..." shown for 2 seconds after a `partner_typing` event (send `typing` at most once per second).
  - Header shows partner: `Riya · 21 · 🇮🇳 India`
  - Online user count shown on home screen.
- Mobile friendly (works on phone screens), dark mode optional.

---

## 11. Backend details

- `main.py`:
  - Create FastAPI app, add CORS for `http://localhost:5173` and the future Vercel URL.
  - `GET /health` returns `{"status": "ok"}`.
  - `WebSocket /ws` handles the protocol above.
  - Broadcast `online_count` every 10 seconds or when count changes.
- Use Pydantic models to validate `join` data.
- `requirements.txt`: `fastapi`, `uvicorn[standard]`, `pytest`, `pytest-asyncio`.

---

## 12. How to run locally

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev                     # opens http://localhost:5173
```

Test with two browser windows (one normal, one incognito), one as Male, one as Female.

---

## 13. Tests to write (backend/tests/test_matcher.py)

- Male + Female with matching filters → matched
- Male + Male → NOT matched
- Female + Female → NOT matched
- Age outside A's range → NOT matched
- Age outside B's range (but inside A's) → NOT matched (mutual check)
- Country filter empty on both → matched
- A filters "IN", B is from "US" → NOT matched
- Oldest compatible waiting user is picked first
- User who disconnects is removed from waiting list
- "next" does not immediately re-pair the same two users
- Age 17 on join → rejected with error

---

## 14. Acceptance checklist

- [ ] Profile form validates all fields, age 18 to 99, gender only Male/Female
- [ ] Filters for country (multi-select + "Any") and age range work
- [ ] Male only ever matches Female and vice versa
- [ ] Filters are respected both ways
- [ ] Messages appear instantly on both sides
- [ ] Next, Stop, Report buttons work
- [ ] Partner leaving shows "Stranger has disconnected"
- [ ] Typing indicator works
- [ ] Online count shows
- [ ] Rate limit works
- [ ] All matcher tests pass
- [ ] Works on mobile screen size

---

## 15. Build order (do one phase at a time)

1. **Phase 1:** Backend skeleton: FastAPI, `/health`, `/ws` that echoes messages back. Test with a simple client.
2. **Phase 2:** `matcher.py` with compatibility check + queue + unit tests. All tests must pass.
3. **Phase 3:** Wire matcher into `/ws`: join, matched, message forwarding, disconnect cleanup.
4. **Phase 4:** React app: ProfileForm → WaitingScreen → ChatRoom using `useChatSocket`.
5. **Phase 5:** Next / Stop / Report, typing indicator, online count, rate limiting.
6. **Phase 6:** Styling, mobile layout, polish.
7. **Phase 7:** Deployment notes: backend on Render (start command `uvicorn main:app --host 0.0.0.0 --port $PORT`), frontend on Vercel with `VITE_WS_URL=wss://<render-url>/ws`.

## 16. Future ideas (NOT for v1)

Redis for queue when running multiple servers, interest tags, dark mode toggle, emoji picker, blocked-words list admin, PWA install.
