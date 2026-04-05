"""Equity, pot-odds and expected-value calculations for Texas Hold'em.

Equity is estimated via Monte Carlo simulation: random opponent hands and
remaining community cards are sampled thousands of times and the fraction of
outcomes where the hero wins (or ties) is returned.
"""
import random
from typing import Sequence

from .card import Card, Deck, Rank, Suit
from .hand_evaluator import evaluate_hand


def _make_full_deck(exclude: set[Card]) -> list[Card]:
    """Return a shuffled list of all 52 cards except those in *exclude*."""
    deck = [Card(rank, suit) for suit in Suit for rank in Rank if Card(rank, suit) not in exclude]
    random.shuffle(deck)
    return deck


def calculate_equity(
    hole_cards: Sequence[Card],
    community_cards: Sequence[Card],
    num_opponents: int = 1,
    num_simulations: int = 10_000,
) -> float:
    """Estimate the hero's equity via Monte Carlo simulation.

    Args:
        hole_cards: The hero's two hole cards.
        community_cards: 0–5 known community cards.
        num_opponents: Number of active opponents (default 1).
        num_simulations: How many random runouts to simulate.

    Returns:
        Estimated equity as a float in ``[0, 1]``.
    """
    hole_cards = list(hole_cards)
    community_cards = list(community_cards)
    known: set[Card] = set(hole_cards) | set(community_cards)
    needed_community = 5 - len(community_cards)
    cards_per_opp = 2

    wins = ties = 0

    for _ in range(num_simulations):
        deck = _make_full_deck(known)

        # Complete the board
        sim_board = community_cards + deck[:needed_community]
        deck = deck[needed_community:]

        # Deal opponent hands (skip simulation if deck runs short)
        total_opp_cards = num_opponents * cards_per_opp
        if len(deck) < total_opp_cards:
            continue
        opponent_hands = [
            deck[i * cards_per_opp: (i + 1) * cards_per_opp]
            for i in range(num_opponents)
        ]

        hero_best = evaluate_hand(hole_cards + sim_board)
        best_opp = max(evaluate_hand(opp + sim_board) for opp in opponent_hands)

        if hero_best > best_opp:
            wins += 1
        elif hero_best == best_opp:
            ties += 1

    return (wins + ties * 0.5) / num_simulations


def calculate_pot_odds(call_amount: float, pot_size: float) -> float:
    """Return the fraction of the total pot the hero must invest to call.

    This is the **minimum equity** required for a break-even call.

    Examples::

        >>> calculate_pot_odds(20, 80)   # call 20 into an 80-chip pot → 20 %
        0.2
    """
    if call_amount <= 0:
        return 0.0
    return call_amount / (pot_size + call_amount)


def calculate_required_equity(call_amount: float, pot_size: float) -> float:
    """Alias for :func:`calculate_pot_odds` — the break-even equity for a call."""
    return calculate_pot_odds(call_amount, pot_size)


def calculate_implied_odds(
    call_amount: float,
    pot_size: float,
    potential_future_winnings: float,
) -> float:
    """Return implied pot-odds when future bets are factored in.

    *potential_future_winnings* is the additional amount expected to be won
    on later streets if the hero hits their hand.
    """
    if call_amount <= 0:
        return 0.0
    total = pot_size + call_amount + potential_future_winnings
    return call_amount / total


def calculate_ev(equity: float, pot_size: float, call_amount: float) -> float:
    """Calculate the expected value (EV) of calling.

    A positive EV means calling is profitable in the long run.

    Args:
        equity: Hero's equity as a fraction in ``[0, 1]``.
        pot_size: Chips already in the pot (not including the call).
        call_amount: Amount the hero must put in to call.

    Returns:
        Expected chips won (positive) or lost (negative) per call.
    """
    return equity * pot_size - (1.0 - equity) * call_amount
