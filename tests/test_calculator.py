"""Tests for the equity and odds calculator."""
import pytest
from poker.card import Card
from poker.calculator import (
    calculate_equity,
    calculate_ev,
    calculate_implied_odds,
    calculate_pot_odds,
    calculate_required_equity,
)


def cards(*strings: str) -> list[Card]:
    return [Card.from_string(s) for s in strings]


# ------------------------------------------------------------------
# Pot-odds / EV functions (deterministic)
# ------------------------------------------------------------------

class TestPotOdds:
    def test_basic_pot_odds(self):
        # Call 20 into pot of 80 → 20 / 100 = 0.20
        assert calculate_pot_odds(20, 80) == pytest.approx(0.20)

    def test_no_call(self):
        assert calculate_pot_odds(0, 100) == 0.0

    def test_required_equity_matches_pot_odds(self):
        assert calculate_required_equity(30, 70) == pytest.approx(calculate_pot_odds(30, 70))

    def test_implied_odds_reduces_required_equity(self):
        normal = calculate_pot_odds(20, 80)
        implied = calculate_implied_odds(20, 80, potential_future_winnings=100)
        assert implied < normal

    def test_implied_odds_zero_call(self):
        assert calculate_implied_odds(0, 100, 50) == 0.0


class TestExpectedValue:
    def test_positive_ev_when_equity_exceeds_pot_odds(self):
        # equity=0.6, pot=100, call=30 → 0.6*100 - 0.4*30 = 60-12 = +48
        ev = calculate_ev(0.6, 100, 30)
        assert ev == pytest.approx(48.0)

    def test_negative_ev_when_under_pot_odds(self):
        # equity=0.1, pot=50, call=50 → 0.1*50 - 0.9*50 = 5-45 = -40
        ev = calculate_ev(0.1, 50, 50)
        assert ev == pytest.approx(-40.0)

    def test_zero_ev_at_breakeven(self):
        # pot odds = 0.5, equity = 0.5, pot=100, call=100
        # 0.5*100 - 0.5*100 = 0
        ev = calculate_ev(0.5, 100, 100)
        assert ev == pytest.approx(0.0)


# ------------------------------------------------------------------
# Monte Carlo equity (stochastic — use generous tolerances)
# ------------------------------------------------------------------

class TestMonteCarloEquity:
    """Monte Carlo tests use enough simulations for statistical reliability."""

    def test_aces_preflop_high_equity(self):
        # AA vs random hand: ~85 % equity
        hole = cards("Ah", "Ad")
        eq = calculate_equity(hole, [], num_opponents=1, num_simulations=3_000)
        assert eq > 0.75, f"AA equity too low: {eq:.2%}"

    def test_72o_low_equity(self):
        # 7-2 offsuit (worst hand): < 40 % equity
        hole = cards("7h", "2d")
        eq = calculate_equity(hole, [], num_opponents=1, num_simulations=3_000)
        assert eq < 0.40, f"72o equity too high: {eq:.2%}"

    def test_equity_lower_with_more_opponents(self):
        # Same hand should have lower equity vs 3 opponents than vs 1
        hole = cards("Ah", "Kd")
        eq1 = calculate_equity(hole, [], num_opponents=1, num_simulations=2_000)
        eq3 = calculate_equity(hole, [], num_opponents=3, num_simulations=2_000)
        assert eq1 > eq3, "Equity should decrease with more opponents"

    def test_royal_flush_on_board(self):
        # Hero has Ah Kh with Qh Jh Th on board (royal flush) — near-unbeatable
        hole = cards("Ah", "Kh")
        board = cards("Qh", "Jh", "Th")
        eq = calculate_equity(hole, board, num_opponents=1, num_simulations=1_000)
        assert eq > 0.95, f"Royal flush equity too low: {eq:.2%}"

    def test_equity_between_zero_and_one(self):
        hole = cards("Tc", "9c")
        eq = calculate_equity(hole, [], num_opponents=2, num_simulations=500)
        assert 0.0 <= eq <= 1.0
