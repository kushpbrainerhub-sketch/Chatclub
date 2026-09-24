"""
FastAPI app: the /health check and the /ws WebSocket (SPEC sections 6, 8, 9, 11).

Start it with:   uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import os
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from filters import censor
from matcher import Matcher, User
from models import JoinRequest, clean_message_text, friendly_error

# ---------- settings ----------

MAX_MESSAGES_PER_SECOND = 5
MAX_NEXT_PER_MINUTE = 10
REPORTS_BEFORE_KICK = 3
ONLINE_COUNT_INTERVAL = 10  # seconds

# Comma separated list, e.g. "http://localhost:5173,https://my-app.vercel.app"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")


# ---------- in-memory state ----------

@dataclass
class Connection:
    """Everything we know about one open browser tab."""
    id: str
    ws: WebSocket
    user: User | None = None  # set after a valid "join"
    message_times: deque = field(default_factory=deque)
    next_times: deque = field(default_factory=deque)
    reports_received: int = 0
    reported_ids: set = field(default_factory=set)  # people THIS user reported


connections: dict[str, Connection] = {}
matcher = Matcher()


# ---------- small helpers ----------

async def send(conn_id: str, data: dict) -> None:
    """Send JSON to one user. Never crashes if their socket is already gone."""
    conn = connections.get(conn_id)
    if conn is None:
        return
    try:
        await conn.ws.send_json(data)
    except Exception:
        pass  # they disconnected; their own cleanup will run


async def send_error(conn_id: str, message: str) -> None:
    await send(conn_id, {"type": "error", "message": message})


async def broadcast_online_count() -> None:
    data = {"type": "online_count", "count": len(connections)}
    for conn_id in list(connections):
        await send(conn_id, data)


def rate_limited(times: deque, limit: int, window_seconds: float) -> bool:
    """
    Sliding window rate limit.
    Returns True if this action should be BLOCKED.
    """
    now = time.monotonic()
    while times and now - times[0] > window_seconds:
        times.popleft()
    if len(times) >= limit:
        return True
    times.append(now)
    return False


def public_profile(user: User) -> dict:
    """What the partner is allowed to see about you."""
    return {
        "username": user.profile.username,
        "age": user.profile.age,
        "country": user.profile.country,
        "gender": user.profile.gender,
    }


async def end_chat(conn_id: str) -> None:
    """Take a user out of the queue / chat and tell their partner."""
    partner_id = await matcher.leave(conn_id)
    if partner_id:
        await send(partner_id, {"type": "partner_left"})


async def start_matching(conn: Connection) -> None:
    """Put the user in the queue, or pair them right away if someone fits."""
    partner = await matcher.join(conn.user)
    if partner is None:
        await send(conn.id, {"type": "waiting"})
        return
    await send(conn.id, {"type": "matched", "partner": public_profile(partner)})
    await send(partner.id, {"type": "matched", "partner": public_profile(conn.user)})


# ---------- one handler per client event type ----------

async def handle_join(conn: Connection, data: dict) -> None:
    try:
        request = JoinRequest(profile=data.get("profile"), filters=data.get("filters") or {})
    except ValidationError as error:
        await send_error(conn.id, friendly_error(error))
        return
    await end_chat(conn.id)  # in case they were already chatting
    conn.user = User(id=conn.id, profile=request.profile, filters=request.filters)
    await start_matching(conn)


async def handle_message(conn: Connection, data: dict) -> None:
    partner_id = matcher.partner_of(conn.id)
    if partner_id is None:
        await send_error(conn.id, "You are not in a chat")
        return
    if rate_limited(conn.message_times, MAX_MESSAGES_PER_SECOND, 1):
        await send_error(conn.id, "Slow down! You are sending messages too fast")
        return
    try:
        text = clean_message_text(data.get("text"))
    except ValueError as error:
        await send_error(conn.id, str(error))
        return
    await send(partner_id, {"type": "message", "text": censor(text), "from": "partner"})


async def handle_typing(conn: Connection) -> None:
    partner_id = matcher.partner_of(conn.id)
    if partner_id:
        await send(partner_id, {"type": "partner_typing"})


async def handle_next(conn: Connection) -> None:
    if conn.user is None:
        await send_error(conn.id, "Please fill in your profile first")
        return
    if rate_limited(conn.next_times, MAX_NEXT_PER_MINUTE, 60):
        await send_error(conn.id, "Too many skips. Please wait a moment and try again")
        return
    await end_chat(conn.id)
    await start_matching(conn)  # same profile and filters as before


async def handle_leave(conn: Connection) -> None:
    await end_chat(conn.id)
    # "Stop" is a fresh start, so they may meet their last partner again later.
    if conn.user:
        conn.user.last_partner_id = None


async def handle_report(conn: Connection, data: dict) -> None:
    partner_id = matcher.partner_of(conn.id)
    if partner_id is None:
        await send_error(conn.id, "You can only report someone you are chatting with")
        return
    if partner_id in conn.reported_ids:
        return  # one report per person is enough
    conn.reported_ids.add(partner_id)

    reported = connections.get(partner_id)
    if reported is None:
        return
    reported.reports_received += 1
    reason = str(data.get("reason", "no reason"))[:100]
    name = reported.user.profile.username if reported.user else "?"
    print(f"[REPORT] {conn.id} reported {partner_id} ({name}) "
          f"reason={reason!r} total={reported.reports_received}")

    if reported.reports_received >= REPORTS_BEFORE_KICK:
        print(f"[KICK] {partner_id} ({name}) disconnected after too many reports")
        await send_error(partner_id, "You were disconnected because several people reported you")
        await end_chat(partner_id)
        try:
            await reported.ws.close(code=4000)
        except Exception:
            pass


# ---------- the app ----------

async def online_count_loop() -> None:
    """Background task: send the online count every few seconds."""
    while True:
        await asyncio.sleep(ONLINE_COUNT_INTERVAL)
        await broadcast_online_count()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(online_count_loop())
    yield
    task.cancel()


app = FastAPI(title="Chatclub", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    conn = Connection(id=uuid.uuid4().hex, ws=ws)
    connections[conn.id] = conn
    await broadcast_online_count()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(conn.id, "Invalid message format")
                continue
            if not isinstance(data, dict):
                await send_error(conn.id, "Invalid message format")
                continue

            kind = data.get("type")
            if kind == "join":
                await handle_join(conn, data)
            elif kind == "message":
                await handle_message(conn, data)
            elif kind == "typing":
                await handle_typing(conn)
            elif kind == "next":
                await handle_next(conn)
            elif kind == "leave":
                await handle_leave(conn)
            elif kind == "report":
                await handle_report(conn, data)
            else:
                await send_error(conn.id, f"Unknown event type: {kind}")
    except WebSocketDisconnect:
        pass
    except RuntimeError:
        pass  # socket was closed by us (e.g. kicked after reports)
    finally:
        # Runs no matter how the connection ended (tab closed, wifi lost, kicked...)
        await end_chat(conn.id)
        connections.pop(conn.id, None)
        await broadcast_online_count()
