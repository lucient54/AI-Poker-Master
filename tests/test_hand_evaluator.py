"""Tests for the hand evaluator."""
import pytest
from poker.card import Card
from poker.hand_evaluator import (
    HandRank,
    compare_hands,
    evaluate_5_cards,
    evaluate_hand,
    hand_name,
)


def cards(*strings: str) -> list[Card]:
    return [Card.from_string(s) for s in strings]


# ------------------------------------------------------------------
# Five-card classifications
# ------------------------------------------------------------------

class TestFiveCardHands:
    def test_royal_flush(self):
        result = evaluate_5_cards(cards("Ah", "Kh", "Qh", "Jh", "Th"))
        assert result[0] == HandRank.ROYAL_FLUSH

    def test_straight_flush(self):
        result = evaluate_5_cards(cards("9h", "8h", "7h", "6h", "5h"))
        assert result[0] == HandRank.STRAIGHT_FLUSH

    def test_four_of_a_kind(self):
        result = evaluate_5_cards(cards("Ah", "Ad", "As", "Ac", "Kh"))
        assert result[0] == HandRank.FOUR_OF_A_KIND

    def test_full_house(self):
        result = evaluate_5_cards(cards("Ah", "Ad", "As", "Kc", "Kh"))
        assert result[0] == HandRank.FULL_HOUSE

    def test_flush(self):
        result = evaluate_5_cards(cards("Ah", "9h", "7h", "5h", "3h"))
        assert result[0] == HandRank.FLUSH

    def test_straight(self):
        result = evaluate_5_cards(cards("9s", "8h", "7d", "6c", "5h"))
        assert result[0] == HandRank.STRAIGHT

    def test_straight_high_is_top_card(self):
        result = evaluate_5_cards(cards("9s", "8h", "7d", "6c", "5h"))
        assert result[1] == [9]

    def test_wheel_straight(self):
        result = evaluate_5_cards(cards("Ah", "5d", "4c", "3h", "2s"))
        assert result[0] == HandRank.STRAIGHT
        assert result[1] == [5]  # high card of wheel is 5

    def test_three_of_a_kind(self):
        result = evaluate_5_cards(cards("Ah", "Ad", "As", "Kc", "Qh"))
        assert result[0] == HandRank.THREE_OF_A_KIND

    def test_two_pair(self):
        result = evaluate_5_cards(cards("Ah", "Ad", "Kc", "Kh", "Qh"))
        assert result[0] == HandRank.TWO_PAIR

    def test_one_pair(self):
        result = evaluate_5_cards(cards("Ah", "Ad", "Kc", "Qh", "2h"))
        assert result[0] == HandRank.ONE_PAIR

    def test_high_card(self):
        result = evaluate_5_cards(cards("Ah", "Kd", "Qc", "Jh", "9s"))
        assert result[0] == HandRank.HIGH_CARD


# ------------------------------------------------------------------
# Seven-card evaluation
# ------------------------------------------------------------------

class TestSevenCardHands:
    def test_best_hand_from_seven(self):
        # Full house is best from these 7 cards
        result = evaluate_hand(cards("Ah", "Ad", "As", "Kc", "Kh", "9d", "7s"))
        assert result[0] == HandRank.FULL_HOUSE

    def test_flush_hidden_in_seven(self):
        # Flush buried in community cards
        result = evaluate_hand(cards("Ah", "Kh", "Qh", "Jh", "9h", "2d", "3c"))
        assert result[0] == HandRank.FLUSH

    def test_best_of_seven_needs_five(self):
        with pytest.raises(ValueError):
            evaluate_hand(cards("Ah", "Kd", "Qc", "Jh"))


# ------------------------------------------------------------------
# Hand rankings (ordering)
# ------------------------------------------------------------------

class TestHandOrdering:
    def test_royal_flush_beats_straight_flush(self):
        rf = cards("Ah", "Kh", "Qh", "Jh", "Th")
        sf = cards("9h", "8h", "7h", "6h", "5h")
        assert evaluate_5_cards(rf) > evaluate_5_cards(sf)

    def test_straight_flush_beats_quads(self):
        sf = cards("9h", "8h", "7h", "6h", "5h")
        quads = cards("Ah", "Ad", "As", "Ac", "Kh")
        assert evaluate_5_cards(sf) > evaluate_5_cards(quads)

    def test_quads_beat_full_house(self):
        quads = cards("Ah", "Ad", "As", "Ac", "Kh")
        fh = cards("Ah", "Ad", "As", "Kc", "Kh")
        assert evaluate_5_cards(quads) > evaluate_5_cards(fh)

    def test_full_house_beats_flush(self):
        fh = cards("Ah", "Ad", "As", "Kc", "Kh")
        flush = cards("Ah", "9h", "7h", "5h", "3h")
        assert evaluate_5_cards(fh) > evaluate_5_cards(flush)

    def test_flush_beats_straight(self):
        flush = cards("Ah", "9h", "7h", "5h", "3h")
        straight = cards("9s", "8h", "7d", "6c", "5h")
        assert evaluate_5_cards(flush) > evaluate_5_cards(straight)

    def test_straight_beats_trips(self):
        straight = cards("9s", "8h", "7d", "6c", "5h")
        trips = cards("Ah", "Ad", "As", "Kc", "Qh")
        assert evaluate_5_cards(straight) > evaluate_5_cards(trips)

    def test_trips_beat_two_pair(self):
        trips = cards("Ah", "Ad", "As", "Kc", "Qh")
        two_pair = cards("Ah", "Ad", "Kc", "Kh", "Qh")
        assert evaluate_5_cards(trips) > evaluate_5_cards(two_pair)

    def test_two_pair_beats_one_pair(self):
        two_pair = cards("Ah", "Ad", "Kc", "Kh", "Qh")
        one_pair = cards("Ah", "Ad", "Kc", "Qh", "2h")
        assert evaluate_5_cards(two_pair) > evaluate_5_cards(one_pair)

    def test_one_pair_beats_high_card(self):
        pair = cards("Ah", "Ad", "Kc", "Qh", "2h")
        high = cards("Ah", "Kd", "Qc", "Jh", "9s")
        assert evaluate_5_cards(pair) > evaluate_5_cards(high)


# ------------------------------------------------------------------
# Tiebreakers
# ------------------------------------------------------------------

class TestTiebreakers:
    def test_higher_pair_wins(self):
        aces = cards("Ah", "Ad", "Kc", "Qh", "Jh")
        kings = cards("Kc", "Kd", "Ah", "Qh", "Jh")
        assert evaluate_5_cards(aces) > evaluate_5_cards(kings)

    def test_same_pair_better_kicker_wins(self):
        ace_k = cards("Ah", "Ad", "Kc", "Qh", "2h")
        ace_q = cards("Ah", "Ad", "Qc", "Jh", "2d")
        assert evaluate_5_cards(ace_k) > evaluate_5_cards(ace_q)

    def test_same_hand_is_tie(self):
        h1 = cards("Ah", "Ad", "Kc", "Qh", "Jh")
        h2 = cards("As", "Ac", "Kd", "Qs", "Js")
        assert evaluate_5_cards(h1) == evaluate_5_cards(h2)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def test_hand_name_full_house():
    h = cards("Ah", "Ad", "As", "Kc", "Kh")
    assert hand_name(h) == "Full House"


def test_compare_hands_win():
    h1 = cards("Ah", "Ad", "As", "Kc", "Kh")
    h2 = cards("Ah", "Kd", "Qc", "Jh", "9s")
    assert compare_hands(h1, h2) == 1


def test_compare_hands_lose():
    h1 = cards("Ah", "Kd", "Qc", "Jh", "9s")
    h2 = cards("Ah", "Ad", "As", "Kc", "Kh")
    assert compare_hands(h1, h2) == -1


def test_compare_hands_tie():
    h1 = cards("Ah", "Kd", "Qc", "Jh", "9s")
    h2 = cards("As", "Ks", "Qd", "Js", "9c")
    assert compare_hands(h1, h2) == 0
