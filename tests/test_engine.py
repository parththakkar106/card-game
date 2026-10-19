import pytest

from app import engine
from app.engine import Illegal

S, H, D, C = 0, 1, 2, 3


def card(r, s, deck=0):
    """Build a card id from a rank (1 to 13), a suit, and a deck number."""
    return deck * 52 + s * 13 + r - 1


def game(hands, table=(), pile=None):
    """Return a state with fixed hands, table groups, and draw pile."""
    state = engine.new_game({"decks": 2, "hand": 7, "timer": 60}, len(hands), seed=1)
    state["hands"] = [list(h) for h in hands]
    state["table"] = [{"id": i + 1, "cards": list(g)} for i, g in enumerate(table)]
    state["next_gid"] = len(table) + 1
    state["pile"] = list(pile if pile is not None else [card(13, D, 1)])
    return state


def play(state, seat, *actions):
    for a in actions:
        state, _ = engine.apply(state, seat, a)
    return state


def move(c, to):
    return {"type": "move", "card": c, "to": to}


@pytest.mark.parametrize("cards, ok", [
    ([card(1, H), card(2, H), card(3, H)], True),
    ([card(12, H), card(13, H), card(1, H)], True),
    ([card(13, H), card(1, H), card(2, H)], False),  # no wrap
    ([card(4, H), card(5, H)], False),
    ([card(4, H), card(5, H), card(7, H)], False),
    ([card(4, H), card(5, S), card(6, H)], False),
    ([card(4, H), card(5, H), card(5, H, 1), card(6, H)], False),
    ([card(9, S), card(9, H), card(9, D)], True),
    ([card(9, S), card(9, H), card(9, D), card(9, C)], True),
    ([card(9, S), card(9, S, 1), card(9, D)], False),  # same suit twice
    ([card(9, S), card(9, H), card(9, D), card(9, C), card(9, S, 1)], False),
])
def test_groups(cards, ok):
    assert engine.is_valid(cards) is ok


@pytest.mark.parametrize("cards, why", [
    ([card(9, S), card(9, H), card(9, D)], None),
    ([card(4, H), card(5, H)], "needs 3 cards"),
    ([card(9, S), card(9, S, 1), card(9, D)], "suit repeats"),
    ([card(4, H), card(5, H), card(7, H)], "not in sequence"),
    ([card(4, H), card(5, S), card(6, H)], "mixed suits"),
    ([card(7, S), card(7, H), card(8, S)], "mixed ranks"),
])
def test_problem_names_the_broken_rule(cards, why):
    assert engine.problem(cards) == why


def test_sort_puts_high_ace_last():
    q, k, a = card(12, H), card(13, H), card(1, H)
    assert engine.sort_group([a, k, q]) == [q, k, a]


def test_settings_keep_half_the_pile():
    assert engine.check_settings({"decks": 1, "hand": 13, "timer": 60}, 2) is None
    assert "2 decks" in engine.check_settings({"decks": 1, "hand": 13, "timer": 60}, 3)
    assert engine.check_settings({"decks": 3, "hand": 15, "timer": 60}, 10)


def test_seed_replays_the_same_deal():
    a = engine.new_game(engine.DEFAULTS, 2, seed=42)
    assert a == engine.new_game(engine.DEFAULTS, 2, seed=42)
    assert a != engine.new_game(engine.DEFAULTS, 2, seed=43)
    assert len(a["pile"]) == 52 - 26


def test_view_hides_other_hands():
    state = engine.new_game({"decks": 2, "hand": 13, "timer": 60}, 4, seed=3)
    v = engine.view(state, 1)
    assert v["hand"] == state["hands"][1]
    assert v["counts"] == [13, 13, 13, 13]
    assert "hands" not in v and "pile" in v and isinstance(v["pile"], int)
    assert engine.view(state, None)["hand"] is None


def test_first_play_must_be_runs():
    hand = [card(9, S), card(9, H), card(9, D), card(4, C)]
    state = game([hand, [card(2, C)] * 3])
    state = play(state, 0, move(hand[0], "new"), move(hand[1], 1), move(hand[2], 1))
    with pytest.raises(Illegal, match="runs only"):
        engine.apply(state, 0, {"type": "end_turn"})


def test_play_then_win():
    hand = [card(4, H), card(5, H), card(6, H)]
    state = game([hand, [card(2, C)] * 5])
    state = play(state, 0, move(hand[0], "new"), move(hand[1], 1), move(hand[2], 1),
                 {"type": "end_turn"})
    assert state["result"] == {"winner": 0}
    assert state["table"][0]["cards"] == hand


def test_manipulation_splits_a_run():
    # The table holds 4-5-6-7-8 of hearts. Seat 0 adds a second 6 of hearts
    # from another deck and splits the run into 4-5-6 and 6-7-8.
    run = [card(r, H) for r in range(4, 9)]
    six = card(6, H, 1)
    state = game([[six, card(1, C)], [card(2, C)] * 3], table=[run])
    state = play(state, 0, move(six, 1), move(card(7, H), "new"), move(card(8, H), 2))
    assert not engine.view(state, 0)["table"][0]["valid"]  # 4-5-6-6
    with pytest.raises(Illegal, match="not valid"):
        engine.apply(state, 0, {"type": "end_turn"})
    # Move the duplicate 6 into the 7-8 group to make 4-5-6 and 6-7-8.
    state = play(state, 0, move(six, 2), {"type": "end_turn"})
    groups = sorted(g["cards"] for g in state["table"])
    assert groups == sorted([[card(4, H), card(5, H), card(6, H)], [six, card(7, H), card(8, H)]])
    assert state["turn"] == 1 and state["hands"][0] == [card(1, C)]


def test_table_cards_never_reach_a_hand():
    run = [card(r, H) for r in range(4, 8)]
    state = game([[card(8, H)], [card(2, C)]], table=[run])
    with pytest.raises(Illegal, match="Table cards"):
        engine.apply(state, 0, move(card(4, H), "hand"))
    # A card placed from the hand this turn may go back.
    state = play(state, 0, move(card(8, H), 1), move(card(8, H), "hand"))
    assert engine.view(state, 0)["hand"] == [card(8, H)]


def test_must_add_a_card_from_hand():
    run = [card(r, H) for r in range(4, 8)]
    state = game([[card(1, C)], [card(2, C)]], table=[run])
    state = play(state, 0, move(card(7, H), "new"), move(card(7, H), 1))
    with pytest.raises(Illegal, match="at least one card"):
        engine.apply(state, 0, {"type": "end_turn"})


def test_only_the_current_seat_moves():
    state = game([[card(1, C)], [card(2, C)]])
    with pytest.raises(Illegal, match="not your turn"):
        engine.apply(state, 1, {"type": "draw"})
    with pytest.raises(Illegal, match="isn't yours"):
        engine.apply(state, 0, move(card(2, C), "new"))


def test_draw_reverts_the_table_and_reports_privately():
    run = [card(r, H) for r in range(4, 8)]
    top = card(13, S)
    state = game([[card(8, H)], [card(2, C)]], table=[run], pile=[top])
    state = play(state, 0, move(card(8, H), 1))
    state, event = engine.apply(state, 0, {"type": "timeout"})
    assert state["table"][0]["cards"] == run
    assert state["hands"][0] == [card(8, H), top]
    assert event["private"]["card"] == top and event["timeout"]
    assert state["turn"] == 1


def test_everyone_passing_on_an_empty_pile_ends_with_no_winner():
    state = game([[card(1, C)], [card(2, C)], [card(3, C)]], pile=[])
    state = play(state, 0, {"type": "draw"})
    state = play(state, 1, {"type": "draw"})
    assert state["result"] is None
    state = play(state, 2, {"type": "draw"})
    assert state["result"] == {"winner": None}


def test_reset_restores_the_turn_start():
    hand = [card(4, H), card(5, H), card(6, H)]
    state = game([hand + [card(1, C)], [card(2, C)]])
    state = play(state, 0, move(hand[0], "new"), {"type": "reset"})
    v = engine.view(state, 0)
    assert v["table"] == [] and v["hand"] == hand + [card(1, C)]
