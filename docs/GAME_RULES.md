# Game rules

This page states the rules as `app/engine.py` enforces them. If the two ever
disagree, the code is wrong or this page is out of date. Fix one of them.

## Setup

- The game uses 1 to 3 standard 52-card decks, shuffled together.
- Each player gets 7 to 15 cards. The default is 13.
- At least half the cards must stay in the draw pile after the deal.
- Seat 0 plays first, then turns go around the table in seat order.

## Groups

| Group | Rule | Valid | Not valid |
| --- | --- | --- | --- |
| Run | 3 or more consecutive cards of one suit | 4♥ 5♥ 6♥, Q♠ K♠ A♠ | K♠ A♠ 2♠ |
| Set | 3 or 4 cards of one rank, no suit twice | 9♠ 9♥ 9♦ | 9♠ 9♠ 9♦ |

With more than one deck, two identical cards can sit in two different runs.

## Your turn

You either play or draw.

**Play.** You can move any card on the table to another group or to a new
group. You can move cards from your hand to the table, and you can take back a
card you placed this turn. Each move reaches every player as it happens. To end
the turn:

1. You added at least one card from your hand.
2. Every group on the table is valid.
3. If the table was empty when your turn started, every group is a run.

If any check fails, the server keeps your turn going and tells you why.
**Reset** puts the table and your hand back to the start of your turn.

**Draw.** You take the top card of the pile, and your turn ends. Any cards you
moved go back where they were. If the pile is empty, the button reads **Pass**
and you take nothing.

**Timer.** When your time runs out, the server draws for you. If you are
disconnected on your turn, the server draws for you after 10 seconds.

## End of the game

- The first player to empty their hand wins.
- If the pile is empty and every player passes once in a row, the game ends
  with no winner.
- The host can press **Rematch** to return everyone to the lobby.
