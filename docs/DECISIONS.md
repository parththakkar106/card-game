# Decisions

These decisions were settled on 2026-10-12 in the project's design thread.
Each entry states the decision and the reason. If you want to change one, edit
it here first, then update the other docs.

## Rules

**D-1. One to three standard decks, no jokers.** The host picks the deck count
in the lobby. Jokers come later as a lobby option.

**D-2. Thirteen cards each, and the host picks 7 to 15.** The lobby refuses to
start unless at least half the cards stay in the draw pile. Reason: a short
pile ends the game in passes before anyone can build.

**D-3. Runs and sets.** A run is 3 or more consecutive cards of one suit. The
ace is low (A-2-3) or high (Q-K-A), with no wrap. A set is 3 or 4 cards of one
rank with no repeated suit. Identical cards from two decks can sit in two
different runs, but never in the same set.

**D-4. The first play of the game is runs only.** There is no point minimum,
and the play can use any cards. Only the opening play of the whole game has
this limit. The server reads "the first group must be a run" as "every group
in the opening play is a run," because the order of groups inside one turn is
not visible.

**D-5. You play or you draw.** To play, you rearrange any table cards and add
at least one card from your hand. Every group must be valid when you end the
turn. Table cards never go to a hand. Drawing one card ends your turn, and it
puts the table back as it was.

**D-6. A 60-second turn timer, and the host picks 30, 60, 90, or none.** When
the time runs out, the table reverts and you draw one card.

**D-7. The first player to empty their hand wins.** There is no ranking of the
other players. If the pile is empty and every player passes once in a row, the
game ends with no winner.

## Rooms and players

**D-8. Guests only.** A player types a name, and a cookie remembers it. The
cookie also holds a random guest id that never reaches other players.

**D-9. Rooms use a 5-character code and a share link.** A room has 2 to 10
seats. The host edits the settings, the other players ready up, and the host
starts. A settings change clears every ready flag, so nobody starts with
settings they did not see.

**D-10. The game never pauses.** A disconnected player keeps their seat for the
whole game and rejoins from the same link. On their turn, the server waits 10
seconds and then draws for them. Reason: with 10 players, a pause stalls nine
people.

**D-11. The next online seat becomes host when the host leaves.**

**D-12. Late arrivals watch.** A spectator sees the table, whose turn it is, and
each player's card count, never a hand.

**D-13. Everyone watches each move live.** Every drag is one message, and the
server relays it to the whole room.

**D-14. Preset reactions only.** Players send one of six emoji, at most one
every 2 seconds. There is no free-text chat.

**D-15. Rematch returns the room to the lobby.** Settings stay the same.
Spectators take free seats, and seats whose player left are freed. Reason:
people who watched one game can join the next.

## Architecture

**D-16. The server holds all game state.** The browser receives only its own
hand plus public information, and it holds no copy of the rules.

**D-17. One snapshot on join, then small change messages.** See the message
list in [ARCHITECTURE.md](ARCHITECTURE.md#socket-messages).

**D-18. A pure rules engine with a seeded shuffle.** `app/engine.py` does no
I/O. A seed plus the list of actions replays a game exactly. A bot can later be
a function that receives `engine.view(state, seat)` and returns an action.

**D-19. No database in v1.** Rooms live in memory in one process. A restart
ends every game.

**D-20. React, Vite, and GSAP for the front end.** All motion code is in
`web/src/motion.js`, so you can retune it or swap the library without touching
game code.

**D-21. Showdown's Pulp Arena look, with every token in one file.** The tokens
are in `web/src/theme.css`. Card faces are drawn in code, with no image files.

**D-22. Desktop first, playable on a phone held sideways.**
