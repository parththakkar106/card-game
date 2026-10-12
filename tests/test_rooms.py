from fastapi.testclient import TestClient

from app import rooms
from app.main import app


def lobby(n):
    code = rooms.create(now=0)
    room = rooms.rooms[code]
    for i in range(n):
        rooms.connect(room, f"g{i}", f"P{i}", 0)
    return room


def start(room):
    for s in room["seats"]:
        rooms.handle(room, s["gid"], {"type": "ready", "ready": True}, 0)
    out = rooms.handle(room, "g0", {"type": "start"}, 0)
    assert out == [("snapshots", None)], out
    return room


def test_host_passes_to_next_seat():
    room = lobby(3)
    assert room["seats"][0]["host"]
    rooms.disconnect(room, "g0", 0)
    assert room["seats"][1]["host"] and not room["seats"][0]["host"]


def test_late_arrival_watches():
    room = start(lobby(2))
    rooms.connect(room, "late", "Late", 0)
    assert rooms.seat_of(room, "late") is None
    snap = rooms.snapshot(room, "late", 0)
    assert snap["game"]["hand"] is None and snap["game"]["counts"] == [13, 13]
    assert rooms.handle(room, "late", {"type": "draw"}, 0)[0][1]["type"] == "error"


def test_only_ready_rooms_start():
    room = lobby(2)
    out = rooms.handle(room, "g0", {"type": "start"}, 0)
    assert out[0][1]["message"] == "Wait until everyone is ready."
    out = rooms.handle(room, "g1", {"type": "settings", "hand": 9}, 0)
    assert out[0][1]["message"] == "Only the host can do that."


def test_timeout_draws_and_passes_the_turn():
    room = start(lobby(2))
    assert rooms.tick(room, 59) == []
    out = rooms.tick(room, 60)
    private = [p for t, p in out if t == ("seat", 0)]
    assert private and len(private[0]["hand"]) == 14
    turn = [p for t, p in out if t == "all"][0]
    assert turn["turn"] == 1 and turn["last"] == {"seat": 0, "how": "timeout"}


def test_away_player_draws_after_ten_seconds():
    room = start(lobby(2))
    room["settings"]["timer"] = 0
    room["deadline"] = None
    rooms.disconnect(room, "g0", 5)
    assert rooms.tick(room, 14) == []
    assert rooms.tick(room, 15)
    assert room["game"]["turn"] == 1


def test_stale_lobby_seat_frees_up():
    room = lobby(3)
    rooms.disconnect(room, "g1", 0)
    assert rooms.drop_stale_seats(room, rooms.LOBBY_GRACE_S - 1) == []
    rooms.drop_stale_seats(room, rooms.LOBBY_GRACE_S)
    assert [s["gid"] for s in room["seats"]] == ["g0", "g2"]


def test_socket_game_flow():
    a, b = TestClient(app), TestClient(app)
    for c, name in ((a, "Ann"), (b, "Bo")):
        assert c.post("/api/me", json={"name": name}).status_code == 200
    code = a.post("/api/rooms").json()["code"]
    with a.websocket_connect(f"/ws/{code}") as wa:
        assert wa.receive_json()["room"]["you"] == 0
        wa.receive_json()  # room summary after the join
        with b.websocket_connect(f"/ws/{code}") as wb:
            assert wb.receive_json()["room"]["you"] == 1
            wb.receive_json()
            assert len(wa.receive_json()["seats"]) == 2
            wb.send_json({"type": "ready", "ready": True})
            wa.receive_json(), wb.receive_json()
            wa.send_json({"type": "start"})
            sa, sb = wa.receive_json(), wb.receive_json()
            assert sa["type"] == "snapshot" and len(sa["game"]["hand"]) == 13
            assert set(sa["game"]["hand"]).isdisjoint(sb["game"]["hand"])
            card = sa["game"]["hand"][0]
            wa.send_json({"type": "move", "card": card, "to": "new"})
            moved = wb.receive_json()
            assert moved["type"] == "moved" and moved["groups"][0]["cards"] == [card]
            assert moved["counts"] == [12, 13]
            wa.receive_json()
            wa.send_json({"type": "end_turn"})
            assert wa.receive_json()["type"] == "error"
            wa.send_json({"type": "draw"})
            mine = wa.receive_json()
            assert mine["type"] == "hand" and len(mine["hand"]) == 14
            turn = wb.receive_json()
            assert turn["type"] == "turn" and turn["table"] == [] and "drew" not in turn
    assert a.get("/healthz").status_code == 200
    rooms.rooms.pop(code)
