"""Player representation."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .card import Card


class Player:
    """Represents one player at the table."""

    def __init__(self, name: str, chips: int = 1000, is_human: bool = False) -> None:
        self.name = name
        self.chips = chips
        self.is_human = is_human
        self.hole_cards: list[Card] = []
        self.current_bet = 0   # chips placed in the current betting round
        self.total_wagered = 0  # chips placed in the current hand total
        self.folded = False
        self.all_in = False

    # ------------------------------------------------------------------
    # Reset helpers
    # ------------------------------------------------------------------

    def reset_for_hand(self) -> None:
        """Clear hand-level state before each new hand."""
        self.hole_cards = []
        self.current_bet = 0
        self.total_wagered = 0
        self.folded = False
        self.all_in = False

    def reset_for_round(self) -> None:
        """Clear round-level bet counter (used internally by the game engine)."""
        self.current_bet = 0

    # ------------------------------------------------------------------
    # Betting
    # ------------------------------------------------------------------

    def bet(self, amount: int) -> int:
        """Commit *amount* chips to the pot.

        Automatically caps at available chips (all-in).
        Returns the actual amount committed.
        """
        amount = max(0, min(amount, self.chips))
        self.chips -= amount
        self.current_bet += amount
        self.total_wagered += amount
        if self.chips == 0:
            self.all_in = True
        return amount

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.name}({self.chips})"

    def __repr__(self) -> str:
        return str(self)
