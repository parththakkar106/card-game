# Architecture

## Overview

One Python process runs everything. It serves the built React files, a small
JSON API for names and rooms, and one WebSocket per open game page. Rooms live
in a dict in memory.

```
browser ──HTTP──▶ /api/me, /api/rooms        (name cookie, new room code)
browser ──WS────▶ /ws/{code}                  (lobby and game messages)
                     │
                     ▼
              app/rooms.py   seats, lobby, timers, message building
                     │
                     ▼
              app/engine.py  every rule, no I/O
```

## Repo layout

| Path | Contents |
| --- | --- |
| `app/engine.py` | The rules engine. Pure functions over a state dict. |
| `app/rooms.py` | Rooms, seats, host handover, the clock, and the messages each event produces. |
| `app/main.py` | FastAPI routes, the socket loop, message delivery, and the clock task. |
| `tests/` | pytest for the engine, the rooms, and one socket game. |
| `web/src/theme.css` | Every color, font, border, and shadow token. |
| `web/src/motion.js` | All GSAP code: drag, flip animations, and effects. |
| `web/src/useRoom.js` | The socket connection and the reducer that applies server messages. |
| `web/src/Table.jsx`, `Lobby.jsx`, `App.jsx` | The screens. |

## Cards

A card is an int. With `d` decks, ids run from 0 to `52 * d - 1`. The rank is
`id % 13 + 1`, and the suit is `(id % 52) // 13` in the order spades, hearts,
diamonds, clubs. Two identical cards from different decks have different ids,
so the client can animate each one.

## Engine

`engine.new_game(settings, players, seed)` shuffles with `random.Random(seed)`
and deals. `engine.apply(state, seat, action)` returns `(new_state, event)` or
raises `engine.Illegal` with a reason for the player. It never changes its
input. `engine.view(state, seat)` returns what one seat may see. A spectator
passes `None`.

During a turn, the state holds `work`: the current player's working copy of
the table and hand. `end_turn` checks `work` and commits it. `draw`, `timeout`,
and `reset` discard it.

## Socket messages

The client connects to `/ws/{code}`. The server reads the `gid` and `name`
cookies. A guest with a seat reconnects to it. In the lobby, a new guest takes
a free seat. Anyone else watches.

### Client to server

| `type` | Fields | Who |
| --- | --- | --- |
| `ready` | `ready` | Any seat, in the lobby |
| `settings` | `decks`, `hand`, `timer` | Host, in the lobby |
| `start` | | Host, in the lobby |
| `move` | `card`, `to` (group id, `"new"`, or `"hand"`) | Current player |
| `reset`, `end_turn`, `draw` | | Current player |
| `react` | `emoji` | Any seat |
| `rematch` | | Host, after the game |
| `ping` | | Anyone, every 20 s |

### Server to client

| `type` | Sent to | Fields |
| --- | --- | --- |
| `snapshot` | One connection, on join and at game start | `room`, `game` (that seat's view), `seconds` |
| `room` | Everyone, on lobby or seat changes | `phase`, `settings`, `seats`, `you` |
| `moved` | Everyone | `seat`, `card`, `from`, `to`, `groups` (changed groups with `valid`), `removed`, `counts` |
| `table` | Everyone, after a reset | `table`, `counts` |
| `hand` | The acting seat only | `hand`, `drew` |
| `turn` | Everyone, when a turn ends | `turn`, `table`, `counts`, `pile`, `seconds`, `last`, `result` |
| `react` | Everyone | `seat`, `emoji` |
| `error` | The sender only | `message`, `about` |

Close codes: `4001` means no name cookie, `4002` means the room opened in
another tab, and `4004` means no such room.

## Timing

A clock task in `app/main.py` calls `rooms.tick` and `rooms.drop_stale_seats`
for every room twice a second. `tick` draws for the current player when the
turn timer runs out or when they have been offline for 10 seconds. In the
lobby, a seat whose player stays offline for 20 seconds is freed.

## Front-end motion

Before the client applies any message that moves cards, `useRoom.js` calls
`motion.capture()`, which records every card's position with GSAP Flip. After
React renders, `Table.jsx` calls `motion.play()`, which animates each card
from its old position to its new one. A dragged card keeps its drag offset
until the server answers, so it animates from where you dropped it. If the
server refuses the move, `motion.snapBack` returns it.

## Hosting (later)

React builds to static files in `web/dist`, which FastAPI serves, so the
server needs Node only at build time. One uvicorn process behind Caddy for
HTTPS fits the Oracle free server.
