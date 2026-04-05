#!/usr/bin/env python3
"""AI Poker Master — interactive Texas Hold'em advisor.

Usage::

    python main.py

Card format: ``Rank + Suit``  (e.g. ``Ah`` = Ace of Hearts, ``Kd`` = King of Diamonds)

    Ranks : 2-9, T (Ten), J (Jack), Q (Queen), K (King), A (Ace)
    Suits : c (clubs), d (diamonds), h (hearts), s (spades)
"""
from poker.ai import PokerAI, PokerPosition
from poker.card import Card


_POSITION_MAP = {
    "early": PokerPosition.EARLY,
    "middle": PokerPosition.MIDDLE,
    "late": PokerPosition.LATE,
    "blind": PokerPosition.BLIND,
}


def _parse_cards(s: str) -> list[Card]:
    """Parse a space-separated string of card tokens into :class:`Card` objects."""
    tokens = s.strip().split()
    return [Card.from_string(t) for t in tokens]


def _prompt_int(msg: str, default: int) -> int:
    raw = input(msg).strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def interactive() -> None:
    print("=" * 60)
    print("  AI POKER MASTER — Texas Hold'em Advisor")
    print("=" * 60)
    print()
    print("  Card format: Rank + Suit  (e.g. Ah Kd Tc 9s 2h)")
    print("  Ranks: 2–9 T J Q K A     Suits: c d h s")
    print()

    ai = PokerAI(name="PokerBot Pro", aggression=0.65, tightness=0.55, num_simulations=6_000)

    while True:
        print("\n─── New Hand Analysis " + "─" * 38)

        # Hole cards
        while True:
            raw = input("  Your hole cards (e.g. Ah Kd): ").strip()
            try:
                hole = _parse_cards(raw)
                if len(hole) != 2:
                    print("  ⚠  Please enter exactly 2 cards.")
                    continue
                break
            except (ValueError, KeyError):
                print("  ⚠  Invalid format — try again (e.g. Ah Kd).")

        # Community cards
        while True:
            raw = input("  Community cards (Enter to skip): ").strip()
            if not raw:
                board: list[Card] = []
                break
            try:
                board = _parse_cards(raw)
                if len(board) not in (0, 3, 4, 5):
                    print("  ⚠  Enter 0, 3, 4 or 5 community cards.")
                    continue
                break
            except (ValueError, KeyError):
                print("  ⚠  Invalid format — try again.")

        # Numeric inputs
        opponents = _prompt_int("  Opponents (default 1): ", 1)
        pot = _prompt_int("  Pot size  (default 100): ", 100)
        to_call = _prompt_int("  Call amount (0 = can check, default 0): ", 0)

        # Position
        print("  Positions: early | middle | late | blind")
        pos_raw = input("  Your position (default middle): ").strip().lower()
        position = _POSITION_MAP.get(pos_raw, PokerPosition.MIDDLE)

        print("\n  Running Monte Carlo equity simulation …\n")
        output = ai.analyze_hand(
            hole, board, to_call, pot,
            num_opponents=opponents, position=position,
        )
        print(output)

        again = input("\n  Analyze another hand? [y/N]: ").strip().lower()
        if again != "y":
            print("\n  Good luck at the tables!\n")
            break


if __name__ == "__main__":
    interactive()
