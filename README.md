# Card Game

Manipulation Rummy for 2 to 10 players in the browser. You create a room,
share the code or link, and everyone plays from their own screen. On your turn
you rearrange the table and add cards from your hand, or you draw.

`card-game` is a working name. Rename the repo once you pick a real one.

**Status (2026-10-12):** Phase 1 is done. Two or more players can create a
room, ready up, and play a full game in the browser.
**Next step:** Start Phase 2 in [docs/PLAN.md](docs/PLAN.md).

## Start here next session

Read these files in order:

1. [docs/DECISIONS.md](docs/DECISIONS.md): every product decision, with the
   reason for each. Read it first so you do not reopen settled questions.
2. [docs/GAME_RULES.md](docs/GAME_RULES.md): the rules as the server enforces
   them.
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): the stack, the repo layout,
   and every socket message.
4. [docs/PLAN.md](docs/PLAN.md): phases with checklists. Tick the boxes as you
   finish them.

## Run it locally

You need Python 3.12 and Node 22.

```bash
python -m venv .venv
pip install -r requirements-dev.txt
cd web && npm install && npm run build && cd ..
uvicorn app.main:app --reload
```

Open http://localhost:8000. To play against yourself, open a second browser
profile or a private window, because each guest is one cookie.

For front-end work, run `npm run dev` in `web/` as well and open
http://localhost:5173. Vite reloads the page on each save and passes API and
socket traffic to the Python server.

`pytest` runs the rules engine and socket tests. While the server runs,
`npm run e2e` in `web/` plays a short two-player game in Chromium.

## Stack in one line

Python 3.12, FastAPI, native WebSockets, React with Vite, GSAP, no database,
and GitHub Actions for tests.
