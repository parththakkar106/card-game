# Build plan

Work through the phases in order. Tick a box when the item works, not when the
code is written.

## Phase 1: Playable game

Goal: friends can play a full game in their browsers on one local server.

- [x] Rules engine with a seeded shuffle and pytest coverage.
- [x] Rooms, lobby settings, ready up, and host start.
- [x] Server-checked moves, relayed live to every player.
- [x] Turn timer, away draws, host handover, and spectators.
- [x] React table with GSAP drag and flip animation in the Pulp Arena look.
- [x] Preset reactions with a rate limit.
- [x] Rematch.
- [x] GitHub Actions runs the tests and the front-end build.

## Phase 2: Hosting

Goal: the game runs at a public HTTPS address.

- [x] Add a Dockerfile that builds `web/` and runs uvicorn. See [DEPLOY.md](DEPLOY.md).
- [x] Set up the Oracle free server with Caddy for HTTPS and WebSockets.
- [x] Deploy from `main` on each merge.

## Phase 3: Polish

- [ ] Deal animation from the pile to each hand at game start.
- [ ] A short flight from a seat badge to the table when another player places
      a card from their hand.
- [x] Sound effects, with a mute toggle.
- [ ] An end-to-end browser test that plays a turn with two players.
- [x] A rules sheet that opens over the table.

## Phase 4: Bots

A bot is a function that receives `engine.view(state, seat)` and returns a
list of actions.

- [ ] Easy: plays complete runs and sets from its own hand.
- [ ] Medium: also adds single cards to table groups.
- [ ] Hard: searches table rearrangements with a time limit.
- [ ] The host adds bots to empty seats in the lobby.

## Later

- [ ] Jokers as a lobby option.
- [ ] Match history with SQLite.
- [ ] Pick the real name and rename the repo.
