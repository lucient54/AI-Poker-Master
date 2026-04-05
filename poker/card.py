"""Card, Rank, Suit and Deck representations for Texas Hold'em."""
import random
from enum import IntEnum


class Suit(IntEnum):
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


_SUIT_SYMBOLS = {
    Suit.CLUBS: "c",
    Suit.DIAMONDS: "d",
    Suit.HEARTS: "h",
    Suit.SPADES: "s",
}

_RANK_SYMBOLS = {
    Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
    Rank.TEN: "T", Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
}

_RANK_PARSE: dict[str, int] = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "t": 10, "J": 11, "j": 11, "Q": 12, "q": 12,
    "K": 13, "k": 13, "A": 14, "a": 14,
}

_SUIT_PARSE: dict[str, int] = {
    "c": 0, "C": 0,
    "d": 1, "D": 1,
    "h": 2, "H": 2,
    "s": 3, "S": 3,
}


class Card:
    """A single playing card identified by rank and suit."""

    __slots__ = ("rank", "suit")

    def __init__(self, rank: int, suit: int) -> None:
        self.rank = Rank(rank)
        self.suit = Suit(suit)

    # ------------------------------------------------------------------ repr
    def __repr__(self) -> str:
        return f"{_RANK_SYMBOLS[self.rank]}{_SUIT_SYMBOLS[self.suit]}"

    def __str__(self) -> str:
        return repr(self)

    # ------------------------------------------------------------------ eq / hash
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    # ------------------------------------------------------------------ factory
    @classmethod
    def from_string(cls, s: str) -> "Card":
        """Parse a card from a two-character string such as ``'Ah'``, ``'Td'``, ``'2s'``."""
        s = s.strip()
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s!r}")
        rank = _RANK_PARSE.get(s[0])
        suit = _SUIT_PARSE.get(s[1])
        if rank is None or suit is None:
            raise ValueError(f"Invalid card string: {s!r}")
        return cls(rank, suit)


class Deck:
    """A standard 52-card deck that can be shuffled and dealt from."""

    def __init__(self) -> None:
        self.cards: list[Card] = [
            Card(rank, suit) for suit in Suit for rank in Rank
        ]
        self.shuffle()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        """Remove and return the top *n* cards from the deck."""
        if n > len(self.cards):
            raise ValueError(f"Cannot deal {n} cards; only {len(self.cards)} remain.")
        dealt, self.cards = self.cards[:n], self.cards[n:]
        return dealt

    def remove(self, cards: list[Card]) -> None:
        """Remove specific cards from the deck (used when some cards are already known)."""
        card_set = set(cards)
        self.cards = [c for c in self.cards if c not in card_set]

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return f"Deck({len(self.cards)} cards)"
