"""Odds calculation utilities.

Provides:
  monte_carlo_equity – estimate win probability via random simulation
  pot_odds           – minimum equity needed to break even on a call
"""

import random

from .card import Card, Deck
from .hand_evaluator import best_hand


def monte_carlo_equity(
    hole_cards: list[Card],
    community_cards: list[Card],
    num_opponents: int = 1,
    simulations: int = 800,
) -> float:
    """Estimate the probability of winning via Monte Carlo simulation.

    Returns a float in [0, 1] representing the fraction of simulations
    in which *hole_cards* beat (or tie) all opponents.
    """
    if num_opponents < 1:
        return 1.0

    cards_needed_from_deck = (5 - len(community_cards)) + num_opponents * 2
    wins = 0
    ties = 0

    for _ in range(simulations):
        deck = Deck()
        deck.remove(hole_cards + community_cards)

        if len(deck) < cards_needed_from_deck:
            # Edge case: not enough cards left (shouldn't normally happen)
            continue

        # Sample required cards at once for speed
        sample = random.sample(deck.cards, cards_needed_from_deck)
        idx = 0

        sim_community = community_cards + sample[idx: idx + (5 - len(community_cards))]
        idx += 5 - len(community_cards)

        my_score, _ = best_hand(hole_cards, sim_community)

        best_opp = None
        for _ in range(num_opponents):
            opp_hole = sample[idx: idx + 2]
            idx += 2
            opp_score, _ = best_hand(opp_hole, sim_community)
            if best_opp is None or opp_score > best_opp:
                best_opp = opp_score

        if my_score > best_opp:
            wins += 1
        elif my_score == best_opp:
            ties += 1

    total = simulations
    return (wins + ties * 0.5) / total if total > 0 else 0.0


def pot_odds(call_amount: int, pot_size: int) -> float:
    """Return the minimum equity required to break even on a call.

    pot_odds = call_amount / (pot_size + call_amount)

    If call_amount is 0 (free check), returns 0.0 (any equity is sufficient).
    """
    if call_amount <= 0:
        return 0.0
    return call_amount / (pot_size + call_amount)
