"""7-card Texas Hold'em hand evaluator.

Hand categories (higher is better):
  8 – Straight Flush (includes Royal Flush)
  7 – Four of a Kind
  6 – Full House
  5 – Flush
  4 – Straight
  3 – Three of a Kind
  2 – Two Pair
  1 – One Pair
  0 – High Card

Each hand is represented as a comparable tuple, e.g. (6, 10, 8) for
a full house tens-full-of-eights.
"""

from itertools import combinations
from typing import Sequence

from .card import Card

HAND_NAMES = {
    8: 'Straight Flush',
    7: 'Four of a Kind',
    6: 'Full House',
    5: 'Flush',
    4: 'Straight',
    3: 'Three of a Kind',
    2: 'Two Pair',
    1: 'One Pair',
    0: 'High Card',
}


def evaluate_5(cards: Sequence[Card]) -> tuple:
    """Return a comparable rank-tuple for exactly 5 cards."""
    ranks = sorted((c.rank for c in cards), reverse=True)
    suits = [c.suit for c in cards]

    # Group by rank frequency, highest rank first within each count tier
    counts: dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    group_ranks = [r for r, _ in groups]
    group_counts = [c for _, c in groups]

    is_flush = len(set(suits)) == 1

    # Straight detection
    unique = sorted(set(ranks), reverse=True)
    is_straight = False
    straight_high = 0
    if len(unique) == 5:
        if unique[0] - unique[4] == 4:
            is_straight = True
            straight_high = unique[0]
        elif unique == [14, 5, 4, 3, 2]:  # wheel A-2-3-4-5
            is_straight = True
            straight_high = 5

    if is_straight and is_flush:
        return (8, straight_high)
    if group_counts[0] == 4:
        return (7, group_ranks[0], group_ranks[1])
    if group_counts[0] == 3 and group_counts[1] == 2:
        return (6, group_ranks[0], group_ranks[1])
    if is_flush:
        return (5,) + tuple(ranks)
    if is_straight:
        return (4, straight_high)
    if group_counts[0] == 3:
        return (3, group_ranks[0]) + tuple(group_ranks[1:])
    if group_counts[0] == 2 and group_counts[1] == 2:
        return (2, group_ranks[0], group_ranks[1], group_ranks[2])
    if group_counts[0] == 2:
        return (1, group_ranks[0]) + tuple(group_ranks[1:])
    return (0,) + tuple(ranks)


def best_hand(hole_cards: list[Card], community_cards: list[Card]) -> tuple[tuple, tuple[Card, ...]]:
    """Find the best 5-card hand from up to 7 cards.

    Returns (score_tuple, winning_5_card_combo).
    """
    all_cards = hole_cards + community_cards
    best_score: tuple | None = None
    best_combo: tuple[Card, ...] | None = None
    for combo in combinations(all_cards, 5):
        score = evaluate_5(combo)
        if best_score is None or score > best_score:
            best_score = score
            best_combo = combo
    return best_score, best_combo  # type: ignore[return-value]


def hand_name(score: tuple) -> str:
    """Human-readable name for a hand score tuple."""
    return HAND_NAMES[score[0]]
