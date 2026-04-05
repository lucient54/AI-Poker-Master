"""Tests for the PokerAI decision engine."""
import pytest
from poker.ai import PokerAI, PokerPosition
from poker.card import Card


def cards(*strings: str) -> list[Card]:
    return [Card.from_string(s) for s in strings]


@pytest.fixture
def ai() -> PokerAI:
    return PokerAI(name="TestBot", aggression=0.6, tightness=0.5, num_simulations=1_000)


# ------------------------------------------------------------------
# Preflop decisions
# ------------------------------------------------------------------

class TestPreflopDecisions:
    def test_premium_hand_does_not_fold_to_small_bet(self, ai):
        hole = cards("Ah", "Ad")
        dec = ai.decide(hole, [], call_amount=20, pot_size=30, num_opponents=1)
        assert dec["action"] != "fold", "AA should not fold to a small bet"

    def test_weak_hand_folds_to_large_bet(self, ai):
        hole = cards("7h", "2d")
        dec = ai.decide(
            hole, [], call_amount=200, pot_size=20, num_opponents=3,
            position=PokerPosition.EARLY,
        )
        assert dec["action"] == "fold", "72o facing a huge bet should fold"

    def test_can_check_when_no_bet(self, ai):
        hole = cards("7h", "2d")
        dec = ai.decide(hole, [], call_amount=0, pot_size=50)
        assert dec["action"] in ("check", "bet")

    def test_strong_hand_can_raise_preflop(self, ai):
        hole = cards("Kh", "Ks")
        dec = ai.decide(
            hole, [], call_amount=20, pot_size=30, can_raise=True,
            position=PokerPosition.LATE,
        )
        assert dec["action"] in ("raise", "call")


# ------------------------------------------------------------------
# Postflop decisions
# ------------------------------------------------------------------

class TestPostflopDecisions:
    def test_top_set_bets_when_checked_to(self, ai):
        hole = cards("Ah", "Ad")
        board = cards("As", "Kd", "7h")  # top set
        dec = ai.decide(hole, board, call_amount=0, pot_size=100, num_simulations=500)
        assert dec["action"] in ("bet", "check"), "Should bet or check, never fold"

    def test_missed_draw_folds_to_big_bet(self, ai):
        hole = cards("2h", "3d")
        board = cards("Ah", "Kd", "Qc", "Js", "9h")  # completely missed
        dec = ai.decide(
            hole, board, call_amount=500, pot_size=100,
            num_opponents=1, num_simulations=500,
        )
        assert dec["action"] == "fold"

    def test_equity_plausible_on_flop(self, ai):
        hole = cards("Ah", "Kd")
        board = cards("Ah", "7d", "2c")  # top pair top kicker
        dec = ai.decide(hole, board, call_amount=0, pot_size=60, num_simulations=500)
        assert 0.5 < dec["equity"] < 1.0, "TPTK should have strong equity"


# ------------------------------------------------------------------
# Decision structure
# ------------------------------------------------------------------

class TestDecisionStructure:
    def test_all_required_keys_present(self, ai):
        dec = ai.decide(cards("Ah", "Kd"), [], 0, 100)
        for key in ("action", "amount", "equity", "adjusted_equity",
                    "pot_odds", "required_equity", "ev", "hand", "street", "reasoning"):
            assert key in dec, f"Missing key: {key}"

    def test_fold_amount_is_zero(self, ai):
        hole = cards("7h", "2d")
        dec = ai.decide(hole, [], call_amount=300, pot_size=20)
        if dec["action"] == "fold":
            assert dec["amount"] == 0

    def test_check_amount_is_zero(self, ai):
        hole = cards("7h", "2d")
        dec = ai.decide(hole, [], call_amount=0, pot_size=50)
        if dec["action"] == "check":
            assert dec["amount"] == 0

    def test_raise_amount_greater_than_call(self, ai):
        hole = cards("Ah", "Ad")
        dec = ai.decide(hole, [], call_amount=20, pot_size=40, can_raise=True)
        if dec["action"] == "raise":
            assert dec["amount"] > 20

    def test_no_raise_when_can_raise_false(self, ai):
        hole = cards("Ah", "Ad")
        dec = ai.decide(hole, [], call_amount=20, pot_size=40, can_raise=False)
        assert dec["action"] != "raise"


# ------------------------------------------------------------------
# analyze_hand
# ------------------------------------------------------------------

class TestAnalyzeHand:
    def test_returns_string(self, ai):
        result = ai.analyze_hand(cards("Ah", "Kd"), [])
        assert isinstance(result, str)

    def test_contains_expected_sections(self, ai):
        result = ai.analyze_hand(cards("Ah", "Kd"), [])
        assert "STATISTICS" in result
        assert "RECOMMENDATION" in result
        assert "REASONING" in result

    def test_shows_call_amount_when_facing_bet(self, ai):
        result = ai.analyze_hand(cards("Ah", "Kd"), [], call_amount=50, pot_size=100)
        assert "50" in result  # call amount should appear


# ------------------------------------------------------------------
# Position effect
# ------------------------------------------------------------------

def test_late_position_equity_ge_early(ai):
    hole = cards("Ah", "Kd")
    late = ai.decide(hole, [], 0, 100, position=PokerPosition.LATE)
    early = ai.decide(hole, [], 0, 100, position=PokerPosition.EARLY)
    assert late["adjusted_equity"] >= early["adjusted_equity"]
