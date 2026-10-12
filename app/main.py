"""The web server: guest cookies, room creation, the game socket, and the clock.

The browser holds no copy of the rules. It sends one message per action, and
`app/rooms.py` decides what everyone receives.
"""
import asyncio
import contextlib
import re
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import rooms

NAME_PATTERN = r"[A-Za-z0-9_\- ]{2,16}"
COOKIE_AGE = 60 * 60 * 24 * 365
TICK_S = 0.5
DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

# Room code -> guest id -> open socket.
conns: dict = {}


async def _clock():
    """Run timeouts, away draws, and lobby seat cleanup for every room."""
    while True:
        await asyncio.sleep(TICK_S)
        now = time.monotonic()
        for room in list(rooms.rooms.values()):
            out = rooms.tick(room, now) + rooms.drop_stale_seats(room, now)
            if out:
                await deliver(room, out, None)


@contextlib.asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(_clock())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


def _guest(cookies) -> tuple:
    return cookies.get("gid"), cookies.get("name")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "rooms": len(rooms.rooms)}


@app.get("/api/me")
async def me(request: Request):
    return {"name": request.cookies.get("name")}


@app.post("/api/me")
async def set_name(request: Request, response: Response):
    body = await request.json()
    name = " ".join(str(body.get("name", "")).split())
    if not re.fullmatch(NAME_PATTERN, name):
        raise HTTPException(400, "Use 2 to 16 letters, digits, spaces, underscores, or hyphens.")
    # The guest id is the seat key, so it never leaves this cookie. Other
    # players see seat numbers only.
    gid = request.cookies.get("gid") or secrets.token_hex(16)
    response.set_cookie("gid", gid, max_age=COOKIE_AGE, httponly=True, samesite="lax")
    response.set_cookie("name", name, max_age=COOKIE_AGE, samesite="lax")
    return {"name": name}


@app.post("/api/rooms")
async def create_room(request: Request):
    gid, name = _guest(request.cookies)
    if not gid or not name:
        raise HTTPException(401, "Pick a name first.")
    return {"code": rooms.create()}


async def _send(ws: WebSocket, payload: dict) -> None:
    # A socket that closed mid-send is cleaned up by its own handler.
    with contextlib.suppress(Exception):
        await ws.send_json(payload)


async def deliver(room: dict, out: list, self_ws) -> None:
    """Send each `(target, payload)` pair from `app/rooms.py`."""
    now = time.monotonic()
    sockets = conns.get(room["code"], {})
    for target, payload in out:
        if target == "all":
            for ws in list(sockets.values()):
                await _send(ws, payload)
        elif target == "room":
            for gid, ws in list(sockets.items()):
                await _send(ws, rooms.summary(room, gid))
        elif target == "snapshots":
            for gid, ws in list(sockets.items()):
                await _send(ws, rooms.snapshot(room, gid, now))
        elif target == "self":
            if self_ws is not None:
                await _send(self_ws, payload)
        else:
            _, i = target
            ws = sockets.get(room["seats"][i]["gid"])
            if ws is not None:
                await _send(ws, payload)


@app.websocket("/ws/{code}")
async def room_socket(ws: WebSocket, code: str):
    gid, name = _guest(ws.cookies)
    room = rooms.get(code)
    # Accept first. A close before the handshake reaches the browser as a
    # generic failure, and the client cannot tell why.
    await ws.accept()
    if room is None:
        await ws.close(code=4004)
        return
    if not gid or not name:
        await ws.close(code=4001)
        return
    sockets = conns.setdefault(room["code"], {})
    old = sockets.get(gid)
    sockets[gid] = ws
    if old is not None:
        # The same guest opened the room in another tab. The newer tab wins.
        with contextlib.suppress(Exception):
            await old.close(code=4002)
    now = time.monotonic()
    out = rooms.connect(room, gid, name, now)
    await _send(ws, rooms.snapshot(room, gid, now))
    await deliver(room, out, ws)
    try:
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict) or msg.get("type") == "ping":
                continue
            await deliver(room, rooms.handle(room, gid, msg, time.monotonic()), ws)
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        if sockets.get(gid) is ws:
            del sockets[gid]
            await deliver(room, rooms.disconnect(room, gid, time.monotonic()), None)


# The React build. `npm run build` in `web/` writes it. Without a build, the
# API still runs, and `npm run dev` serves the pages instead.
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        return FileResponse(DIST / "index.html")
