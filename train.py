"""Self-play training mode – AI vs AI.

Runs many hands between AI agents with varying aggression/bluff
parameters and records per-hand statistics to a JSONL file for
downstream analysis or model training.

Usage:
    python train.py [--hands N] [--players P] [--chips C] [--out FILE]

Example:
    python train.py --hands 5000 --players 3 --out training_data.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time

from poker.ai_agent import AIAgent
from poker.game import TexasHoldem
from poker.hand_evaluator import best_hand, hand_name
from poker.player import Player


class TrainingGame(TexasHoldem):
    """A TexasHoldem game driven entirely by AI agents."""

    def __init__(
        self,
        players: list[Player],
        agents: dict[str, AIAgent],
        small_blind: int = 10,
        big_blind: int = 20,
    ) -> None:
        super().__init__(players, small_blind, big_blind)
        self.agents = agents
        # Per-session stats
        self.stats: dict[str, dict] = {
            p.name: {'hands_won': 0, 'total_profit': 0, 'hands_played': 0}
            for p in players
        }
        self._hand_start_chips: dict[str, int] = {}

    # ------------------------------------------------------------------

    def _get_action(self, player: Player, to_call: int) -> tuple[str, int]:
        agent = self.agents[player.name]
        num_opp = len([p for p in self.players if not p.folded and p.name != player.name])
        min_raise = to_call + self.big_blind
        max_raise = player.chips
        return agent.get_action(
            player, to_call, self.pot,
            self.community_cards, num_opp,
            min_raise, max_raise,
        )

    def play_hand(self) -> list[str]:
        # Snapshot chips before the hand
        self._hand_start_chips = {p.name: p.chips for p in self.players}
        log = super().play_hand()
        # Update stats
        for p in self.players:
            profit = p.chips - self._hand_start_chips.get(p.name, p.chips)
            self.stats[p.name]['total_profit'] += profit
            self.stats[p.name]['hands_played'] += 1
            if profit > 0:
                self.stats[p.name]['hands_won'] += 1
        return log

    def hand_record(self) -> dict:
        """Return a JSON-serialisable record of the last hand."""
        record: dict = {
            'hand_number': self.hand_number,
            'community': [str(c) for c in self.community_cards],
            'players': [],
        }
        for p in self.players:
            record['players'].append({
                'name': p.name,
                'hole_cards': [str(c) for c in p.hole_cards],
                'chips_before': self._hand_start_chips.get(p.name, 0),
                'chips_after': p.chips,
                'profit': p.chips - self._hand_start_chips.get(p.name, 0),
                'folded': p.folded,
            })
        return record


def print_summary(game: TrainingGame, elapsed: float) -> None:
    print(f"\n{'═'*55}")
    print(f"  Training complete – {game.hand_number} hands in {elapsed:.1f}s")
    print(f"{'═'*55}")
    print(f"  {'Player':<12}  {'Hands':>6}  {'Won':>6}  {'Win%':>6}  {'Profit':>8}  {'Chips':>8}")
    print(f"  {'──────':<12}  {'──────':>6}  {'──────':>6}  {'──────':>6}  {'──────':>8}  {'──────':>8}")
    for p in game.players:
        s = game.stats[p.name]
        wp = s['hands_won'] / s['hands_played'] * 100 if s['hands_played'] else 0
        print(
            f"  {p.name:<12}  {s['hands_played']:>6}  {s['hands_won']:>6}"
            f"  {wp:>5.1f}%  {s['total_profit']:>+8}  {p.chips:>8}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI self-play training for Texas Hold'em")
    parser.add_argument('--hands', type=int, default=1000,
                        help='Number of hands to play (default: 1000)')
    parser.add_argument('--players', type=int, default=3,
                        help='Number of AI players (2-6, default: 3)')
    parser.add_argument('--chips', type=int, default=10000,
                        help='Starting chips per player (default: 10000)')
    parser.add_argument('--sb', type=int, default=25, help='Small blind (default: 25)')
    parser.add_argument('--bb', type=int, default=50, help='Big blind (default: 50)')
    parser.add_argument('--out', type=str, default='',
                        help='Output JSONL file for hand records (optional)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print each hand log to stdout')
    parser.add_argument('--sims', type=int, default=200,
                        help='Monte Carlo simulations per decision (default: 200; '
                             'higher = more accurate but slower)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    num_players = max(2, min(6, args.players))

    # Create players with slightly varied AI personalities
    players: list[Player] = []
    agents: dict[str, AIAgent] = {}
    base_aggression = [0.25, 0.40, 0.55, 0.30, 0.45, 0.20]
    base_bluff = [0.05, 0.10, 0.15, 0.08, 0.12, 0.04]

    for i in range(num_players):
        name = f'AI-{i + 1}'
        p = Player(name, chips=args.chips)
        players.append(p)
        agents[name] = AIAgent(
            aggression=base_aggression[i % len(base_aggression)],
            bluff_rate=base_bluff[i % len(base_bluff)],
            simulations=args.sims,
        )

    game = TrainingGame(players, agents, small_blind=args.sb, big_blind=args.bb)

    print(f"Starting training: {num_players} AI players, {args.hands} hands")
    print(f"Players: {', '.join(p.name for p in players)}")
    print(f"Blinds: {args.sb}/{args.bb}  |  Starting chips: {args.chips}")
    print()

    out_file = open(args.out, 'w') if args.out else None
    start = time.time()
    rebuy_count = 0

    for hand_num in range(1, args.hands + 1):
        # Rebuy any eliminated players so training continues indefinitely
        for p in players:
            if p.chips <= 0:
                p.chips = args.chips
                rebuy_count += 1

        log = game.play_hand()

        if args.verbose:
            print(f"\nHand #{hand_num}")
            for line in log:
                print(f"  {line}")

        if out_file:
            record = game.hand_record()
            out_file.write(json.dumps(record) + '\n')

        if hand_num % 100 == 0:
            elapsed = time.time() - start
            rate = hand_num / elapsed
            print(f"  Hand {hand_num}/{args.hands}  ({rate:.0f} hands/s)  "
                  f"Rebuys: {rebuy_count}")

    if out_file:
        out_file.close()
        size_kb = os.path.getsize(args.out) // 1024
        print(f"\nSaved {args.hands} hand records to '{args.out}' ({size_kb} KB)")

    elapsed = time.time() - start
    print_summary(game, elapsed)


if __name__ == '__main__':
    main()
