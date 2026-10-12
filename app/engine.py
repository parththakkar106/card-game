"""The Manipulation Rummy rules engine.

This module holds every game rule and does no networking or I/O. Each function
takes a game state and returns a new one, or raises `Illegal` with a reason
that a player can read. The state is a plain dict of lists and ints, so it
copies cheaply and serializes to JSON.

A card is an int. With `decks` decks, ids run from 0 to `52 * decks - 1`.
`rank(c)` is 1 (ace) to 13 (king), and `suit(c)` is 0 to 3 (S, H, D, C). Two
cards from different decks with the same rank and suit are distinct ids.

The shuffle uses `random.Random(seed)`, so a seed plus the list of actions
replays a whole game exactly.
"""
import copy
import random

SUITS = "SHDC"

DECKS = (1, 2, 3)
HAND_SIZES = range(7, 16)
TIMERS = (30, 60, 90, 0)  # 0 means no limit.
DEFAULTS = {"decks": 1, "hand": 13, "timer": 60}
MIN_PLAYERS, MAX_PLAYERS = 2, 10


class Illegal(Exception):
    """A move that the rules refuse. The message is shown to the player."""


def rank(c: int) -> int:
    return c % 13 + 1


def suit(c: int) -> int:
    return (c % 52) // 13


def label(c: int) -> str:
    return "A23456789TJQK"[rank(c) - 1].replace("T", "10") + "♠♥♦♣"[suit(c)]


# ---------- Groups ----------

def is_set(cards: list) -> bool:
    """Return True for 3 or 4 cards of one rank with no repeated suit.

    Two identical cards from different decks share a suit, so they never form
    a set together.
    """
    if not 3 <= len(cards) <= 4:
        return False
    return len({rank(c) for c in cards}) == 1 and len({suit(c) for c in cards}) == len(cards)


def is_run(cards: list) -> bool:
    """Return True for 3 or more consecutive cards of one suit.

    The ace counts as 1 or as 14, but not both in one run, so K-A-2 is not a
    run.
    """
    if len(cards) < 3 or len({suit(c) for c in cards}) != 1:
        return False
    for ace in (1, 14):
        values = sorted(ace if rank(c) == 1 else rank(c) for c in cards)
        if all(b == a + 1 for a, b in zip(values, values[1:])):
            return True
    return False


def is_valid(cards: list) -> bool:
    return is_run(cards) or is_set(cards)


def sort_group(cards: list) -> list:
    """Return a group in display order: runs by rank, sets by suit.

    An ace goes after the king when the group holds a king and no 2.
    """
    ranks = {rank(c) for c in cards}
    ace_high = 13 in ranks and 2 not in ranks

    def key(c):
        r = rank(c)
        return (14 if r == 1 and ace_high else r, suit(c), c)

    return sorted(cards, key=key)


# ---------- Settings ----------

def check_settings(settings: dict, players: int) -> str | None:
    """Return a reason the game cannot start, or None.

    At least half the cards must stay in the draw pile after the deal.
    """
    decks, hand, timer = settings["decks"], settings["hand"], settings["timer"]
    if decks not in DECKS or hand not in HAND_SIZES or timer not in TIMERS:
        return "Those settings are out of range."
    if not MIN_PLAYERS <= players <= MAX_PLAYERS:
        return f"A game needs {MIN_PLAYERS} to {MAX_PLAYERS} players."
    if players * hand > decks * 52 // 2:
        need = next((d for d in DECKS if players * hand <= d * 52 // 2), None)
        if need:
            return f"Deal fewer cards or use {need} decks, so half the cards stay in the draw pile."
        return "Deal fewer cards, so half the cards stay in the draw pile."
    return None


# ---------- Game state ----------

def new_game(settings: dict, players: int, seed: int) -> dict:
    """Shuffle, deal, and return the state for seat 0's first turn."""
    error = check_settings(settings, players)
    if error:
        raise Illegal(error)
    pile = list(range(52 * settings["decks"]))
    random.Random(seed).shuffle(pile)
    # The top of the pile is the end of the list, so a draw is `pop()`.
    hands = [[pile.pop() for _ in range(settings["hand"])] for _ in range(players)]
    return {
        "seed": seed, "settings": dict(settings), "players": players,
        "pile": pile, "hands": hands,
        # The table as it stood at the start of the turn. Each group has an id
        # that stays the same while the group exists, so a change message can
        # name it.
        "table": [], "next_gid": 1,
        "turn": 0, "turn_no": 1,
        # The current player's working copy of the table and their hand, or
        # None until they move a card.
        "work": None,
        # Turns in a row that ended with no play while the pile was empty.
        "passes": 0,
        # None while the game runs, then {"winner": seat or None}.
        "result": None,
    }


def _work(state: dict) -> dict:
    if state["work"] is None:
        state["work"] = {"table": copy.deepcopy(state["table"]),
                         "hand": list(state["hands"][state["turn"]])}
    return state["work"]


def current(state: dict) -> tuple:
    """Return `(table, hand)` as the current player sees it right now."""
    w = state["work"]
    if w:
        return w["table"], w["hand"]
    return state["table"], state["hands"][state["turn"]]


def counts(state: dict) -> list:
    """Return each seat's card count, with the current player's live count."""
    n = [len(h) for h in state["hands"]]
    if state["work"]:
        n[state["turn"]] = len(state["work"]["hand"])
    return n


def view(state: dict, seat: int | None) -> dict:
    """Return what one seat may see. `None` is a spectator.

    A bot receives this same view, so it cannot read another hand.
    """
    table, _ = current(state)
    hand = None
    if seat is not None:
        hand = current(state)[1] if seat == state["turn"] and state["work"] else state["hands"][seat]
    return {
        "players": state["players"], "turn": state["turn"], "turn_no": state["turn_no"],
        "pile": len(state["pile"]), "counts": counts(state),
        "table": [public_group(g) for g in table],
        "hand": list(hand) if hand is not None else None,
        "result": state["result"],
    }


def public_group(g: dict) -> dict:
    return {"id": g["id"], "cards": g["cards"], "valid": is_valid(g["cards"])}


# ---------- Actions ----------

def apply(state: dict, seat: int, action: dict) -> tuple:
    """Apply one action for one seat. Return `(new_state, event)`.

    The input state is never changed. `event` describes what happened, for the
    server to turn into change messages. Its `private` key, when present, is
    for the acting seat only.
    """
    if state["result"] is not None:
        raise Illegal("The game is over.")
    if seat != state["turn"]:
        raise Illegal("It's not your turn.")
    handler = {"move": _move, "reset": _reset, "end_turn": _end_turn,
               "draw": _draw, "timeout": _draw}.get(action.get("type"))
    if handler is None:
        raise Illegal("Unknown action.")
    state = copy.deepcopy(state)
    event = handler(state, seat, action)
    return state, event


def _move(state: dict, seat: int, action: dict) -> dict:
    card, to = action.get("card"), action.get("to")
    w = _work(state)
    if card in w["hand"]:
        source = "hand"
    else:
        source = next((g["id"] for g in w["table"] if card in g["cards"]), None)
        if source is None:
            raise Illegal("That card isn't yours to move.")
    if to == source:
        raise Illegal("The card is already there.")
    if to == "hand":
        # Cards placed from your hand this turn may come back. Table cards never
        # go to a hand.
        if card not in state["hands"][seat]:
            raise Illegal("Table cards can't go to a hand.")
        w["hand"].append(card)
    elif to == "new":
        to = state["next_gid"]
        state["next_gid"] += 1
        w["table"].append({"id": to, "cards": [card]})
    else:
        target = next((g for g in w["table"] if g["id"] == to), None)
        if target is None:
            raise Illegal("That group is gone.")
        target["cards"] = sort_group(target["cards"] + [card])
    if source == "hand":
        w["hand"].remove(card)
    else:
        g = next(g for g in w["table"] if g["id"] == source)
        g["cards"] = sort_group([c for c in g["cards"] if c != card])
    removed = [g["id"] for g in w["table"] if not g["cards"]]
    w["table"] = [g for g in w["table"] if g["cards"]]
    changed = [public_group(g) for g in w["table"] if g["id"] in (source, to)]
    return {"type": "moved", "seat": seat, "card": card, "from": source, "to": to,
            "groups": changed, "removed": removed}


def _reset(state: dict, seat: int, action: dict) -> dict:
    state["work"] = None
    return {"type": "reset", "seat": seat}


def _end_turn(state: dict, seat: int, action: dict) -> dict:
    w = state["work"]
    if w is None or len(w["hand"]) >= len(state["hands"][seat]):
        raise Illegal("Add at least one card from your hand, or draw.")
    bad = sum(1 for g in w["table"] if not is_valid(g["cards"]))
    if bad:
        raise Illegal(f"{bad} group{'s are' if bad > 1 else ' is'} not valid yet.")
    # The first play of the game opens the table with runs only.
    if not state["table"] and not all(is_run(g["cards"]) for g in w["table"]):
        raise Illegal("The first play of the game must be runs only.")
    played = len(state["hands"][seat]) - len(w["hand"])
    state["table"], state["hands"][seat] = w["table"], w["hand"]
    state["work"] = None
    state["passes"] = 0
    if not state["hands"][seat]:
        state["result"] = {"winner": seat}
    else:
        _advance(state)
    return {"type": "played", "seat": seat, "played": played}


def _draw(state: dict, seat: int, action: dict) -> dict:
    # Drawing, or running out of time, puts the table back as it was.
    state["work"] = None
    card = None
    if state["pile"]:
        card = state["pile"].pop()
        state["hands"][seat].append(card)
        state["passes"] = 0
    else:
        state["passes"] += 1
        if state["passes"] >= state["players"]:
            state["result"] = {"winner": None}
    if state["result"] is None:
        _advance(state)
    # The hand goes back to the player, because any cards they had placed
    # this turn return to it. Only they learn the drawn card.
    return {"type": "drew" if card is not None else "passed", "seat": seat,
            "timeout": action["type"] == "timeout",
            "private": {"card": card, "hand": list(state["hands"][seat])}}


def _advance(state: dict) -> None:
    state["turn"] = (state["turn"] + 1) % state["players"]
    state["turn_no"] += 1
