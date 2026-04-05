"""Texas Hold'em hand evaluator.

Ranks 5-card (or best-of-7) poker hands from Royal Flush down to High Card.
"""
from collections import Counter
from enum import IntEnum
from itertools import combinations
from typing import Sequence

from .card import Card, Rank


class HandRank(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


# Human-readable names for each HandRank
HAND_RANK_NAMES: dict[HandRank, str] = {
    HandRank.HIGH_CARD: "High Card",
    HandRank.ONE_PAIR: "One Pair",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.THREE_OF_A_KIND: "Three of a Kind",
    HandRank.STRAIGHT: "Straight",
    HandRank.FLUSH: "Flush",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FOUR_OF_A_KIND: "Four of a Kind",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    HandRank.ROYAL_FLUSH: "Royal Flush",
}

# Type alias for a hand evaluation result: (HandRank, tiebreaker list of Rank values)
HandResult = tuple[HandRank, list[int]]


def evaluate_5_cards(cards: Sequence[Card]) -> HandResult:
    """Evaluate a **5-card** hand and return ``(HandRank, tiebreakers)``.

    *tiebreakers* is a list of rank integers ordered so that a simple
    lexicographic comparison correctly breaks ties between equal-rank hands.
    """
    ranks = sorted([int(c.rank) for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    is_flush = len(set(suits)) == 1

    # Straight detection (including A-2-3-4-5 wheel)
    is_straight = False
    straight_high = 0
    if len(set(ranks)) == 5:
        if ranks[0] - ranks[4] == 4:
            is_straight = True
            straight_high = ranks[0]
        elif ranks == [14, 5, 4, 3, 2]:  # wheel: A-2-3-4-5
            is_straight = True
            straight_high = 5

    rank_counts = Counter(ranks)
    # groups sorted by (count desc, rank desc) so kickers naturally follow
    groups: list[int] = sorted(
        rank_counts.keys(),
        key=lambda r: (rank_counts[r], r),
        reverse=True,
    )
    count_values = [rank_counts[r] for r in groups]

    if is_straight and is_flush:
        if straight_high == 14:
            return HandRank.ROYAL_FLUSH, [straight_high]
        return HandRank.STRAIGHT_FLUSH, [straight_high]

    if count_values[0] == 4:
        return HandRank.FOUR_OF_A_KIND, groups

    if count_values[0] == 3 and count_values[1] == 2:
        return HandRank.FULL_HOUSE, groups

    if is_flush:
        return HandRank.FLUSH, ranks

    if is_straight:
        return HandRank.STRAIGHT, [straight_high]

    if count_values[0] == 3:
        return HandRank.THREE_OF_A_KIND, groups

    if count_values[0] == 2 and count_values[1] == 2:
        return HandRank.TWO_PAIR, groups

    if count_values[0] == 2:
        return HandRank.ONE_PAIR, groups

    return HandRank.HIGH_CARD, ranks


def evaluate_hand(cards: Sequence[Card]) -> HandResult:
    """Return the best 5-card hand from 5–7 cards.

    Uses ``evaluate_5_cards`` across all ``C(n,5)`` combinations and returns
    the highest-ranking result.
    """
    if len(cards) == 5:
        return evaluate_5_cards(cards)

    best: HandResult | None = None
    for combo in combinations(cards, 5):
        result = evaluate_5_cards(list(combo))
        if best is None or result > best:
            best = result

    if best is None:
        raise ValueError("Need at least 5 cards to evaluate a hand.")
    return best


def hand_name(cards: Sequence[Card]) -> str:
    """Return a human-readable name for the best hand in *cards*."""
    result = evaluate_hand(cards)
    return HAND_RANK_NAMES.get(result[0], "Unknown")


def compare_hands(hand1: Sequence[Card], hand2: Sequence[Card]) -> int:
    """Compare two hands.

    Returns:
        ``1``  if *hand1* is stronger,
        ``-1`` if *hand2* is stronger,
        ``0``  if they tie.
    """
    h1 = evaluate_hand(hand1)
    h2 = evaluate_hand(hand2)
    if h1 > h2:
        return 1
    if h1 < h2:
        return -1
    return 0
