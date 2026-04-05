"""Pot-odds AI agent for Texas Hold'em.

Decision logic:
  1. Estimate hand equity via Monte Carlo simulation.
  2. Compute pot odds (minimum equity to break even on a call).
  3. If equity > pot_odds + aggression_margin  → raise (with probability = aggression)
     If equity > pot_odds                       → call  (or check if free)
     Otherwise                                  → fold  (or check if free)
  4. A small bluff_rate allows occasional bluffs regardless of equity.
"""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from .odds_calculator import monte_carlo_equity, pot_odds

if TYPE_CHECKING:
    from .card import Card
    from .player import Player


class AIAgent:
    """Rule-based agent that uses pot-odds and hand equity to decide actions."""

    def __init__(
        self,
        aggression: float = 0.35,
        bluff_rate: float = 0.08,
        simulations: int = 600,
    ) -> None:
        """
        Parameters
        ----------
        aggression:
            [0-1] Probability of raising when equity is clearly favourable.
            Higher values produce a more aggressive betting style.
        bluff_rate:
            [0-1] Probability of bluff-betting regardless of hand strength.
        simulations:
            Number of Monte Carlo trials used to estimate hand equity.
            Fewer = faster but noisier; more = slower but more accurate.
        """
        self.aggression = aggression
        self.bluff_rate = bluff_rate
        self.simulations = simulations

    def get_action(
        self,
        player: Player,
        to_call: int,
        pot: int,
        community_cards: list[Card],
        num_opponents: int,
        min_raise: int,
        max_raise: int,
    ) -> tuple[str, int]:
        """Return *(action, amount)* for the given game state.

        *amount* for 'raise' is the **additional chips** the player commits
        on top of *to_call* (i.e. total committed = to_call + amount).
        Callers should pass ``to_call + amount`` to ``player.bet()``.
        """
        # --- Bluff ---
        if random.random() < self.bluff_rate and to_call < player.chips:
            raise_extra = random.randint(min_raise, min(max_raise, min_raise * 3))
            return 'raise', to_call + raise_extra

        # --- Equity & pot odds ---
        equity = monte_carlo_equity(
            player.hole_cards,
            community_cards,
            num_opponents=max(1, num_opponents),
            simulations=self.simulations,
        )
        required = pot_odds(to_call, pot)

        # --- Raise ---
        if equity > required + self.aggression * 0.15:
            if random.random() < self.aggression and player.chips > to_call:
                raise_extra = int(pot * 0.6)
                raise_extra = max(raise_extra, min_raise)
                raise_extra = min(raise_extra, max_raise - to_call)
                if raise_extra > 0:
                    return 'raise', to_call + raise_extra

        # --- Call / Check ---
        if equity >= required:
            if to_call == 0:
                return 'check', 0
            return 'call', to_call

        # --- Fold / Check ---
        if to_call == 0:
            return 'check', 0
        return 'fold', 0
