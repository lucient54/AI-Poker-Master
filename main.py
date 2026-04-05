"""Interactive Texas Hold'em – play against AI opponents.

Usage:
    python main.py [--players N] [--chips C] [--hands H]

Defaults: 2 players (you + 1 AI), 1000 chips each, unlimited hands.
"""

import argparse
import sys

from poker.ai_agent import AIAgent
from poker.game import TexasHoldem
from poker.hand_evaluator import best_hand, hand_name
from poker.player import Player


class InteractiveGame(TexasHoldem):
    """Texas Hold'em where seat 0 is a human and the rest are AI opponents."""

    def __init__(
        self,
        players: list[Player],
        agents: dict[str, AIAgent],
        small_blind: int = 10,
        big_blind: int = 20,
    ) -> None:
        super().__init__(players, small_blind, big_blind)
        self.agents = agents  # name → AIAgent

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    def _get_action(self, player: Player, to_call: int) -> tuple[str, int]:
        if player.is_human:
            return self._human_action(player, to_call)
        return self._ai_action(player, to_call)

    def _human_action(self, player: Player, to_call: int) -> tuple[str, int]:
        print(f"\n{'─'*50}")
        print(f"Your hand : {' '.join(str(c) for c in player.hole_cards)}")
        if self.community_cards:
            print(f"Community : {' '.join(str(c) for c in self.community_cards)}")
        print(f"Pot       : {self.pot}   Chips: {player.chips}   To call: {to_call}")

        # Show current equity estimate
        opponents_active = len([p for p in self.players if not p.folded and p.name != player.name])
        if opponents_active > 0:
            from poker.odds_calculator import monte_carlo_equity, pot_odds
            equity = monte_carlo_equity(
                player.hole_cards, self.community_cards,
                num_opponents=opponents_active, simulations=400,
            )
            needed = pot_odds(to_call, self.pot)
            print(f"Equity    : {equity:.0%}   Pot odds: {needed:.0%}  "
                  f"({'profitable' if equity >= needed else 'unfavourable'})")

        options = ['fold'] if to_call > 0 else []
        options += ['check'] if to_call == 0 else [f'call {to_call}']
        options.append('raise <amount>')
        print(f"Options   : {' | '.join(options)}")

        min_raise_total = to_call + self.big_blind

        while True:
            try:
                raw = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nQuitting game.")
                sys.exit(0)

            parts = raw.split()
            if not parts:
                continue
            cmd = parts[0]

            if cmd == 'fold' and to_call > 0:
                return 'fold', 0
            if cmd == 'check' and to_call == 0:
                return 'check', 0
            if cmd == 'call' and to_call > 0:
                return 'call', to_call
            if cmd == 'raise':
                if len(parts) < 2:
                    print(f"  Usage: raise <amount>  (min {min_raise_total})")
                    continue
                try:
                    amount = int(parts[1])
                except ValueError:
                    print("  Invalid amount.")
                    continue
                if amount < min_raise_total:
                    print(f"  Minimum raise is {min_raise_total}.")
                    continue
                if amount > player.chips:
                    print(f"  You only have {player.chips} chips; going all-in.")
                    amount = player.chips
                return 'raise', amount
            print(f"  Unknown command. Options: {' | '.join(options)}")

    def _ai_action(self, player: Player, to_call: int) -> tuple[str, int]:
        agent = self.agents[player.name]
        num_opp = len([p for p in self.players if not p.folded and p.name != player.name])
        min_raise = to_call + self.big_blind
        max_raise = player.chips

        action, amount = agent.get_action(
            player, to_call, self.pot,
            self.community_cards, num_opp,
            min_raise, max_raise,
        )
        return action, amount

    # ------------------------------------------------------------------
    # Override play_hand to print logs live
    # ------------------------------------------------------------------

    def play_hand(self) -> list[str]:
        log = super().play_hand()
        print(f"\n{'═'*50}")
        print(f"  Hand #{self.hand_number}")
        print(f"{'═'*50}")
        for line in log:
            if line.startswith('\n'):
                print()
                print(line.lstrip('\n'))
            else:
                print(f"  {line}")
        print()
        print("  Chip counts:")
        for p in self.players:
            print(f"    {p.name}: {p.chips}")
        return log


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Play Texas Hold'em vs AI")
    parser.add_argument('--players', type=int, default=2,
                        help='Total number of players including you (2-6)')
    parser.add_argument('--chips', type=int, default=1000,
                        help='Starting chips per player')
    parser.add_argument('--hands', type=int, default=0,
                        help='Number of hands to play (0 = unlimited)')
    parser.add_argument('--sb', type=int, default=10, help='Small blind amount')
    parser.add_argument('--bb', type=int, default=20, help='Big blind amount')
    args = parser.parse_args()

    num_players = max(2, min(6, args.players))

    # Build player list – seat 0 is the human
    players: list[Player] = [Player('You', chips=args.chips, is_human=True)]
    for i in range(1, num_players):
        players.append(Player(f'AI-{i}', chips=args.chips))

    # Build AI agents
    agents: dict[str, AIAgent] = {}
    for p in players:
        if not p.is_human:
            agents[p.name] = AIAgent(aggression=0.35, bluff_rate=0.08, simulations=600)

    game = InteractiveGame(players, agents, small_blind=args.sb, big_blind=args.bb)

    print("╔══════════════════════════════════════╗")
    print("║      AI Poker Master – Texas Hold'em  ║")
    print("╚══════════════════════════════════════╝")
    print(f"Players: {', '.join(p.name for p in players)}")
    print(f"Starting chips: {args.chips}  |  Blinds: {args.sb}/{args.bb}")
    print("Commands: fold | check | call | raise <amount>")
    print()

    hand = 0
    while True:
        # Remove busted players
        busted = [p for p in players if p.chips <= 0]
        for p in busted:
            players.remove(p)
            agents.pop(p.name, None)
            print(f"  {p.name} is eliminated.")

        if len(players) < 2:
            print("Game over – not enough players remaining.")
            break

        human = next((p for p in players if p.is_human), None)
        if human is None:
            print("You have been eliminated. Game over.")
            break

        hand += 1
        if args.hands > 0 and hand > args.hands:
            print(f"Played {args.hands} hands. Exiting.")
            break

        try:
            game.play_hand()
        except KeyboardInterrupt:
            print("\nGame interrupted.")
            break


if __name__ == '__main__':
    main()
