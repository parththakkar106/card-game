"""Rooms, seats, the lobby, and turn timing.

This module keeps rooms in memory and turns engine events into messages. It
sends nothing itself. Each handler returns a list of `(target, payload)`
pairs, and `app/main.py` delivers them. That keeps the rules here testable
without sockets.

Targets:

- `"all"`: every seat and every spectator.
- `("seat", i)`: one seat only. Private hand data uses this target.
- `"room"`: every connection gets the room summary with its own `you` field.
"""
import secrets
import time

from app import engine

# Leave out 0, O, 1, I, and L, which players misread when they type a code.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 5
IDLE_S = 2 * 60 * 60
# A lobby seat waits this long for a dropped player before it frees up. A page
# reload reconnects well inside it.
LOBBY_GRACE_S = 20
# During a game, the server draws for a disconnected player after this delay.
AWAY_DRAW_S = 10
REACTIONS = ("👏", "😂", "😮", "😤", "🔥", "🤝")
REACT_GAP_S = 2.0

rooms: dict = {}


def _sweep(now: float) -> None:
    for code in [c for c, r in rooms.items() if r["touched"] < now - IDLE_S]:
        del rooms[code]


def clean_code(code: str) -> str:
    """Reduce a typed code to the code alphabet, uppercased."""
    return "".join(c for c in code.upper() if c in CODE_ALPHABET)[:CODE_LEN]


def create(now: float | None = None) -> str:
    now = time.monotonic() if now is None else now
    _sweep(now)
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
        if code not in rooms:
            break
    rooms[code] = {
        "code": code, "phase": "lobby", "settings": dict(engine.DEFAULTS),
        # Seat order is turn order. A seat is
        # {gid, name, host, ready, online, gone_at, reacted}.
        "seats": [],
        # Guest id -> name for connected viewers without a seat.
        "watchers": {},
        "game": None, "deadline": None, "turn_started": None,
        "touched": now,
    }
    return code


def get(code: str):
    return rooms.get(clean_code(code))


def seat_of(room: dict, gid: str):
    return next((i for i, s in enumerate(room["seats"]) if s["gid"] == gid), None)


# ---------- Messages ----------

def summary(room: dict, gid: str | None) -> dict:
    return {
        "type": "room", "code": room["code"], "phase": room["phase"],
        "settings": room["settings"],
        "seats": [{"name": s["name"], "host": s["host"], "ready": s["ready"],
                   "online": s["online"]} for s in room["seats"]],
        "you": seat_of(room, gid) if gid else None,
        "reactions": REACTIONS,
    }


def seconds_left(room: dict, now: float):
    if room["deadline"] is None:
        return None
    return max(0, round(room["deadline"] - now))


def snapshot(room: dict, gid: str | None, now: float) -> dict:
    """Return the full state one connection may see. Sent on join and rejoin."""
    seat = seat_of(room, gid) if gid else None
    game = room["game"]
    return {
        "type": "snapshot", "room": summary(room, gid),
        "game": engine.view(game, seat) if game else None,
        "seconds": seconds_left(room, now),
    }


def _turn_message(room: dict, now: float, last: dict) -> dict:
    game = room["game"]
    return {
        "type": "turn", "turn": game["turn"], "turn_no": game["turn_no"],
        "table": [engine.public_group(g) for g in game["table"]],
        "counts": engine.counts(game), "pile": len(game["pile"]),
        "seconds": seconds_left(room, now), "last": last, "result": game["result"],
    }


# ---------- Connections ----------

def connect(room: dict, gid: str, name: str, now: float) -> list:
    """Seat or reconnect a guest, or add them as a watcher."""
    room["touched"] = now
    i = seat_of(room, gid)
    if i is None and room["phase"] == "lobby" and len(room["seats"]) < engine.MAX_PLAYERS:
        room["seats"].append({"gid": gid, "name": name, "host": not room["seats"],
                              "ready": False, "online": True, "gone_at": None, "reacted": 0.0})
    elif i is None:
        room["watchers"][gid] = name
    else:
        s = room["seats"][i]
        s["online"], s["gone_at"] = True, None
    _fix_host(room)
    return [("room", None)]


def disconnect(room: dict, gid: str, now: float) -> list:
    room["watchers"].pop(gid, None)
    i = seat_of(room, gid)
    if i is None:
        return []
    s = room["seats"][i]
    s["online"], s["gone_at"] = False, now
    _fix_host(room)
    return [("room", None)]


def _fix_host(room: dict) -> None:
    """Pass the host role to the next online seat when the host is away."""
    seats = room["seats"]
    host = next((i for i, s in enumerate(seats) if s["host"]), None)
    if host is not None and seats[host]["online"]:
        return
    start = host if host is not None else -1
    for k in range(1, len(seats) + 1):
        j = (start + k) % len(seats)
        if seats[j]["online"]:
            for s in seats:
                s["host"] = False
            seats[j]["host"] = True
            return


# ---------- Player messages ----------

def handle(room: dict, gid: str, msg: dict, now: float) -> list:
    """Handle one message from a connection. Return the messages to send."""
    room["touched"] = now
    i = seat_of(room, gid)
    kind = msg.get("type")
    if i is None:
        return _error(None, "Spectators can only watch.")
    seat = room["seats"][i]
    try:
        if kind == "react":
            return _react(room, i, msg, now)
        if room["phase"] == "lobby":
            return _lobby(room, i, msg, now)
        if kind == "rematch":
            if not seat["host"]:
                raise engine.Illegal("Only the host can start a rematch.")
            if room["phase"] != "over":
                raise engine.Illegal("The game is still going.")
            return _rematch(room)
        if room["phase"] == "playing" and kind in ("move", "undo", "reset", "end_turn", "draw"):
            return _act(room, i, msg, now)
        raise engine.Illegal("That isn't possible right now.")
    except engine.Illegal as e:
        return _error(i, str(e), kind)


def _error(i, message: str, about=None) -> list:
    payload = {"type": "error", "message": message, "about": about}
    return [(("seat", i), payload)] if i is not None else [("self", payload)]


def _react(room: dict, i: int, msg: dict, now: float) -> list:
    seat = room["seats"][i]
    if msg.get("emoji") not in REACTIONS or now - seat["reacted"] < REACT_GAP_S:
        return []
    seat["reacted"] = now
    return [("all", {"type": "react", "seat": i, "emoji": msg["emoji"]})]


def _lobby(room: dict, i: int, msg: dict, now: float) -> list:
    seat, kind = room["seats"][i], msg.get("type")
    if kind == "ready":
        seat["ready"] = bool(msg.get("ready"))
        return [("room", None)]
    if not seat["host"]:
        raise engine.Illegal("Only the host can do that.")
    if kind == "settings":
        settings = dict(room["settings"])
        for key in ("decks", "hand", "timer"):
            if key in msg:
                settings[key] = msg[key]
        if (settings["decks"] not in engine.DECKS or settings["hand"] not in engine.HAND_SIZES
                or settings["timer"] not in engine.TIMERS):
            raise engine.Illegal("Those settings are out of range.")
        room["settings"] = settings
        # Nobody starts a game with settings they did not see.
        for s in room["seats"]:
            s["ready"] = False
        return [("room", None)]
    if kind == "start":
        if any(not s["ready"] for s in room["seats"] if not s["host"]):
            raise engine.Illegal("Wait until everyone is ready.")
        if any(not s["online"] for s in room["seats"]):
            raise engine.Illegal("Someone is still reconnecting.")
        room["game"] = engine.new_game(room["settings"], len(room["seats"]), secrets.randbits(32))
        room["phase"] = "playing"
        _start_turn(room, now)
        return [("snapshots", None)]
    raise engine.Illegal("That isn't possible in the lobby.")


def _rematch(room: dict) -> list:
    """Return everyone to the lobby with the same settings.

    Watchers take free seats, and seats whose player left are freed.
    """
    room["seats"] = [s for s in room["seats"] if s["online"]]
    for s in room["seats"]:
        s["ready"] = False
    for gid, name in list(room["watchers"].items()):
        if len(room["seats"]) < engine.MAX_PLAYERS:
            room["seats"].append({"gid": gid, "name": name, "host": False,
                                  "ready": False, "online": True, "gone_at": None, "reacted": 0.0})
            del room["watchers"][gid]
    _fix_host(room)
    room["phase"], room["game"], room["deadline"] = "lobby", None, None
    return [("snapshots", None)]


def _start_turn(room: dict, now: float) -> None:
    timer = room["settings"]["timer"]
    room["turn_started"] = now
    room["deadline"] = now + timer if timer and room["game"]["result"] is None else None


def _act(room: dict, i: int, msg: dict, now: float) -> list:
    action = {"type": msg["type"]}
    if msg["type"] == "move":
        action.update(card=msg.get("card"), to=msg.get("to"))
    room["game"], event = engine.apply(room["game"], i, action)
    return _publish(room, event, now)


def _publish(room: dict, event: dict, now: float) -> list:
    game = room["game"]
    kind = event["type"]
    if kind == "moved":
        payload = {k: event[k] for k in ("seat", "card", "from", "to", "groups", "removed")}
        return [("all", {"type": "moved", **payload, "counts": engine.counts(game)})]
    if kind == "reset":
        seat = event["seat"]
        table, hand = engine.current(game)
        return [(("seat", seat), {"type": "hand", "hand": list(hand), "drew": None}),
                ("all", {"type": "table", "counts": engine.counts(game),
                         "table": [engine.public_group(g) for g in table]})]
    # The turn ended by a play, a draw, a pass, or a timeout.
    seat = event["seat"]
    out = []
    if "private" in event:
        out.append((("seat", seat), {"type": "hand", "hand": event["private"]["hand"],
                                     "drew": event["private"]["card"]}))
    if game["result"] is not None:
        room["phase"] = "over"
    _start_turn(room, now)
    how = "timeout" if event.get("timeout") else kind
    out.append(("all", _turn_message(room, now, {"seat": seat, "how": how})))
    return out


# ---------- Clock ----------

def tick(room: dict, now: float) -> list:
    """Draw for the current player when their time is up or they are away."""
    game = room["game"]
    if room["phase"] != "playing" or game is None:
        return []
    turn = game["turn"]
    seat = room["seats"][turn]
    late = room["deadline"] is not None and now >= room["deadline"]
    away = not seat["online"] and now >= max(seat["gone_at"], room["turn_started"]) + AWAY_DRAW_S
    if not (late or away):
        return []
    room["game"], event = engine.apply(game, turn, {"type": "timeout"})
    return _publish(room, event, now)


def drop_stale_seats(room: dict, now: float) -> list:
    """Free lobby seats whose player has been gone longer than the grace time."""
    if room["phase"] != "lobby":
        return []
    keep = [s for s in room["seats"] if s["online"] or now - s["gone_at"] < LOBBY_GRACE_S]
    if len(keep) == len(room["seats"]):
        return []
    room["seats"] = keep
    _fix_host(room)
    return [("room", None)]
