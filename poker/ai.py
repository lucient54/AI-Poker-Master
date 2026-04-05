"""Texas Hold'em AI decision engine.

The AI evaluates hand strength using preflop lookup tables and postflop
Monte Carlo equity simulation, then applies game-theoretically motivated
decision logic to recommend fold / check / call / bet / raise.

Strategy parameters ``aggression`` and ``tightness`` let callers tune the
playing style without rewriting decision logic.
"""
from __future__ import annotations

from typing import Sequence

from .calculator import (
    calculate_equity,
    calculate_ev,
    calculate_pot_odds,
    calculate_required_equity,
)
from .card import Card
from .hand_evaluator import HAND_RANK_NAMES, HandRank, evaluate_hand


class PokerPosition:
    """Named position constants."""

    EARLY = "early"
    MIDDLE = "middle"
    LATE = "late"
    BLIND = "blind"


# ---------------------------------------------------------------------------
# Preflop starting-hand strength table
# ---------------------------------------------------------------------------
# Values on a 0–10 scale derived from the Chen formula and expert hand charts.
# Keys are (high_rank_name, low_rank_name); suited bonus added at runtime.
_PREFLOP_STRENGTH: dict[tuple[str, str], float] = {
    # Premium pairs
    ("A", "A"): 10.0, ("K", "K"): 9.5, ("Q", "Q"): 9.0,
    ("J", "J"): 8.5, ("T", "T"): 8.0, ("9", "9"): 7.0,
    ("8", "8"): 6.5, ("7", "7"): 6.0, ("6", "6"): 5.5,
    ("5", "5"): 5.0, ("4", "4"): 4.5, ("3", "3"): 4.0, ("2", "2"): 3.5,
    # Big broadway hands
    ("A", "K"): 8.5, ("A", "Q"): 7.5, ("A", "J"): 7.0, ("A", "T"): 6.5,
    ("A", "9"): 5.5, ("A", "8"): 5.0, ("A", "7"): 4.5, ("A", "6"): 4.0,
    ("A", "5"): 4.5, ("A", "4"): 4.0, ("A", "3"): 3.5, ("A", "2"): 3.5,
    # King-x
    ("K", "Q"): 7.0, ("K", "J"): 6.5, ("K", "T"): 6.0,
    ("K", "9"): 4.5, ("K", "8"): 4.0, ("K", "7"): 3.5,
    # Queen-x
    ("Q", "J"): 6.0, ("Q", "T"): 5.5, ("Q", "9"): 5.0,
    # Jack / Ten connectors
    ("J", "T"): 6.0, ("T", "9"): 5.5, ("9", "8"): 5.0,
    ("8", "7"): 4.5, ("7", "6"): 4.0, ("6", "5"): 3.5,
}

_RANK_NAMES: dict[int, str] = {
    14: "A", 13: "K", 12: "Q", 11: "J", 10: "T",
    9: "9", 8: "8", 7: "7", 6: "6", 5: "5", 4: "4", 3: "3", 2: "2",
}

# Position equity adjustments (additive)
_POSITION_ADJUST: dict[str, float] = {
    PokerPosition.LATE: 0.05,
    PokerPosition.MIDDLE: 0.00,
    PokerPosition.EARLY: -0.03,
    PokerPosition.BLIND: -0.02,
}


class PokerAI:
    """Texas Hold'em AI advisor.

    Args:
        name: Display name for the AI player.
        aggression: 0–1 float controlling bet / raise sizing and frequency.
            Higher values → bigger, more frequent bets.
        tightness: 0–1 float controlling starting-hand selectivity.
            Higher values → fold more marginal hands.
        num_simulations: Monte Carlo trials used for postflop equity estimates.
    """

    def __init__(
        self,
        name: str = "PokerBot",
        aggression: float = 0.6,
        tightness: float = 0.5,
        num_simulations: int = 5_000,
    ) -> None:
        self.name = name
        self.aggression = max(0.0, min(1.0, aggression))
        self.tightness = max(0.0, min(1.0, tightness))
        self.num_simulations = num_simulations

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(
        self,
        hole_cards: Sequence[Card],
        community_cards: Sequence[Card],
        call_amount: float = 0,
        pot_size: float = 100,
        num_opponents: int = 1,
        position: str = PokerPosition.MIDDLE,
        stack_size: float = 1_000,
        can_raise: bool = True,
        num_simulations: int | None = None,
    ) -> dict:
        """Compute the recommended action for the current situation.

        Returns a dictionary with the following keys:

        * ``action`` — ``'fold'``, ``'check'``, ``'call'``, ``'bet'``, or ``'raise'``
        * ``amount`` — chips to bet/raise (0 for fold/check/call)
        * ``equity`` — raw estimated equity (0–1)
        * ``adjusted_equity`` — equity after position adjustment
        * ``pot_odds`` — fraction of pot that a call represents
        * ``required_equity`` — break-even equity for calling
        * ``ev`` — expected value of calling (chips)
        * ``hand`` — human-readable hand description
        * ``street`` — current street name
        * ``reasoning`` — plain-English explanation
        """
        hole_cards = list(hole_cards)
        community_cards = list(community_cards)
        street = _street_name(community_cards)
        sims = num_simulations if num_simulations is not None else self.num_simulations

        # ---- Equity ----
        if street == "preflop":
            equity = self._preflop_strength(hole_cards)
        else:
            equity = calculate_equity(
                hole_cards,
                community_cards,
                num_opponents=num_opponents,
                num_simulations=sims,
            )

        # ---- Pot odds / EV ----
        pot_odds = calculate_pot_odds(call_amount, pot_size)
        required_equity = calculate_required_equity(call_amount, pot_size)
        ev = calculate_ev(equity, pot_size, call_amount)

        # ---- Adjusted equity (position + multi-way discounting) ----
        adj_equity = equity + _POSITION_ADJUST.get(position, 0.0)
        if num_opponents > 1:
            adj_equity = adj_equity / (num_opponents ** 0.5)
        adj_equity = max(0.0, min(1.0, adj_equity))

        hand_desc = _hand_description(hole_cards, community_cards)

        action, amount, reasoning = self._make_decision(
            adj_equity, required_equity, ev,
            call_amount, pot_size, stack_size,
            street, can_raise, hand_desc,
        )

        return {
            "action": action,
            "amount": amount,
            "equity": equity,
            "adjusted_equity": adj_equity,
            "pot_odds": pot_odds,
            "required_equity": required_equity,
            "ev": ev,
            "hand": hand_desc,
            "street": street,
            "reasoning": reasoning,
        }

    def analyze_hand(
        self,
        hole_cards: Sequence[Card],
        community_cards: Sequence[Card],
        call_amount: float = 0,
        pot_size: float = 100,
        num_opponents: int = 1,
        position: str = PokerPosition.MIDDLE,
        stack_size: float = 1_000,
    ) -> str:
        """Return a formatted multi-line analysis of the current hand."""
        decision = self.decide(
            hole_cards, community_cards, call_amount, pot_size,
            num_opponents, position, stack_size,
        )

        lines = [
            "=" * 56,
            f"  AI POKER MASTER — {self.name}",
            "=" * 56,
            f"  Street : {decision['street'].upper()}",
            f"  Hole   : {' '.join(str(c) for c in hole_cards)}",
        ]
        if community_cards:
            lines.append(f"  Board  : {' '.join(str(c) for c in community_cards)}")
        lines += [
            f"  Hand   : {decision['hand']}",
            "",
            "  ── STATISTICS ──────────────────────────────────────",
            f"  Equity vs {num_opponents} opponent(s) : {decision['equity']:.1%}",
            f"  Position-adjusted equity  : {decision['adjusted_equity']:.1%}",
        ]
        if call_amount > 0:
            lines += [
                f"  Pot size                  : {pot_size}",
                f"  Call amount               : {call_amount}",
                f"  Pot odds (break-even eq.) : {decision['required_equity']:.1%}",
                f"  Expected value            : {decision['ev']:+.1f} chips",
            ]
        lines += [
            "",
            "  ── RECOMMENDATION ──────────────────────────────────",
            f"  Action : {decision['action'].upper()}"
            + (f"  {decision['amount']}" if decision["amount"] > 0 else ""),
            "",
            "  ── REASONING ───────────────────────────────────────",
            f"  {decision['reasoning']}",
            "=" * 56,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preflop_strength(self, hole_cards: list[Card]) -> float:
        """Return normalised preflop hand strength in ``[0, 1]``."""
        r1, r2 = int(hole_cards[0].rank), int(hole_cards[1].rank)
        suited = hole_cards[0].suit == hole_cards[1].suit
        hi, lo = (_RANK_NAMES[max(r1, r2)], _RANK_NAMES[min(r1, r2)])

        base = _PREFLOP_STRENGTH.get((hi, lo), _PREFLOP_STRENGTH.get((lo, hi), 3.0))

        # Suited connector / suited hand bonus
        if suited and r1 != r2:
            base += 0.5

        return min(1.0, base / 10.0)

    def _make_decision(
        self,
        equity: float,
        required_equity: float,
        ev: float,
        call_amount: float,
        pot_size: float,
        stack_size: float,
        street: str,
        can_raise: bool,
        hand_desc: str,
    ) -> tuple[str, float, str]:
        """Core decision logic; returns ``(action, amount, reasoning)``."""

        # Thresholds that adapt to the aggression/tightness settings
        raise_threshold = 0.65 + 0.10 * self.tightness - 0.10 * self.aggression
        bet_threshold = 0.55 + 0.10 * self.tightness - 0.10 * self.aggression

        # ---- No bet to face — check or bet ----
        if call_amount <= 0:
            if equity >= bet_threshold and can_raise:
                bet = self._bet_size(equity, pot_size, stack_size)
                return (
                    "bet", bet,
                    f"{hand_desc} (equity {equity:.1%}) — betting {bet} for value "
                    f"({equity:.1%} ≥ bet threshold {bet_threshold:.1%}).",
                )
            return (
                "check", 0,
                f"Checking {hand_desc} (equity {equity:.1%}); "
                "not strong enough to open-bet profitably.",
            )

        # ---- Facing a bet — fold / call / raise ----
        if equity >= raise_threshold and can_raise:
            raise_to = self._raise_size(equity, pot_size, call_amount, stack_size)
            return (
                "raise", raise_to,
                f"Raising to {raise_to}: {hand_desc} equity {equity:.1%} "
                f"exceeds raise threshold {raise_threshold:.1%}.",
            )

        if equity >= required_equity or ev > 0:
            return (
                "call", call_amount,
                f"Calling {call_amount}: equity {equity:.1%} ≥ pot-odds "
                f"{required_equity:.1%} (EV {ev:+.1f}). Hand: {hand_desc}.",
            )

        return (
            "fold", 0,
            f"Folding: equity {equity:.1%} < required {required_equity:.1%} "
            f"(EV {ev:+.1f}). Hand: {hand_desc}.",
        )

    def _bet_size(self, equity: float, pot_size: float, stack_size: float) -> float:
        """Size an opening bet at 33–100 % of pot, scaled by equity."""
        fraction = max(0.33, min(1.0, 0.33 + (equity - 0.5) * 1.34))
        bet = round(pot_size * fraction * (1.0 + 0.5 * self.aggression))
        return min(bet, stack_size)

    def _raise_size(
        self, equity: float, pot_size: float, call_amount: float, stack_size: float
    ) -> float:
        """Size a raise between 2.5× and 4× the facing bet."""
        mult = 2.5 + 1.5 * self.aggression
        raise_to = round(call_amount * mult + pot_size * 0.5)
        return min(raise_to, stack_size)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _street_name(community_cards: list[Card]) -> str:
    return {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(
        len(community_cards), "unknown"
    )


def _hand_description(hole: list[Card], board: list[Card]) -> str:
    if not board:
        return "Preflop"
    result = evaluate_hand(hole + board)
    return HAND_RANK_NAMES.get(result[0], "Unknown")
