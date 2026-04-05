"""Card and Deck representations."""
import random

RANKS = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
    8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
}

SUITS = {0: '\u2660', 1: '\u2665', 2: '\u2666', 3: '\u2663'}  # ♠ ♥ ♦ ♣


class Card:
    """A single playing card."""

    __slots__ = ('rank', 'suit')

    def __init__(self, rank: int, suit: int) -> None:
        self.rank = rank  # 2–14  (2–A)
        self.suit = suit  # 0–3   (♠ ♥ ♦ ♣)

    def __str__(self) -> str:
        return f"{RANKS[self.rank]}{SUITS[self.suit]}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return self.rank * 4 + self.suit


class Deck:
    """Standard 52-card deck."""

    def __init__(self) -> None:
        self.cards: list[Card] = [Card(r, s) for r in range(2, 15) for s in range(4)]
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card] | Card:
        """Deal *n* cards from the top. Returns a list if n > 1, else a single Card."""
        if n == 1:
            return self.cards.pop()
        return [self.cards.pop() for _ in range(n)]

    def remove(self, cards: list[Card]) -> None:
        """Remove specific cards from the deck (used for simulation)."""
        card_set = set(cards)
        self.cards = [c for c in self.cards if c not in card_set]

    def __len__(self) -> int:
        return len(self.cards)
