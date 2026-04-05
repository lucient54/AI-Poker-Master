"""Texas Hold'em game engine.

TexasHoldem is an abstract base class.  Subclasses must implement
``_get_action(player, to_call)`` which returns ``(action, amount)``.

Supported actions
-----------------
  'fold'  – player folds; amount ignored
  'check' – player checks (only valid when to_call == 0)
  'call'  – player calls the current bet; amount ignored (auto-computed)
  'raise' – player raises; amount = **total chips to commit this action**
             (must be >= to_call + big_blind)
"""

from __future__ import annotations

from .card import Deck
from .hand_evaluator import best_hand, hand_name
from .player import Player


class TexasHoldem:
    """Core Texas Hold'em game engine (abstract base class)."""

    def __init__(
        self,
        players: list[Player],
        small_blind: int = 10,
        big_blind: int = 20,
    ) -> None:
        if len(players) < 2:
            raise ValueError("Need at least 2 players.")
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind

        self.deck: Deck | None = None
        self.community_cards: list = []
        self.pot = 0
        self.current_bet = 0
        self.stage = ''
        self.dealer_idx = 0
        self.sb_idx = 0
        self.bb_idx = 0
        self.hand_number = 0
        self.hand_log: list[str] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def play_hand(self) -> list[str]:
        """Play one complete hand and return the hand log."""
        self.hand_number += 1
        self.hand_log = []

        self._reset_hand()
        self._post_blinds()
        self._deal_hole_cards()

        for stage in ('preflop', 'flop', 'turn', 'river'):
            self.stage = stage
            active = [p for p in self.players if not p.folded]
            if len(active) == 1:
                break

            if stage == 'flop':
                self._deal_community(3, burn=True)
                self._log(f"Flop: {self._cards_str(self.community_cards)}")
            elif stage == 'turn':
                self._deal_community(1, burn=True)
                self._log(f"Turn: {self._cards_str(self.community_cards)}")
            elif stage == 'river':
                self._deal_community(1, burn=True)
                self._log(f"River: {self._cards_str(self.community_cards)}")

            result = self._betting_round(stage)
            if result == 'all_fold':
                break

        self._showdown()
        self._move_dealer()
        return self.hand_log

    # ------------------------------------------------------------------
    # Abstract method – subclasses provide this
    # ------------------------------------------------------------------

    def _get_action(self, player: Player, to_call: int) -> tuple[str, int]:
        """Return *(action, amount)* for *player*.

        'amount' is the **total chips committed this action** for a raise.
        It is ignored for fold / check / call.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Hand setup
    # ------------------------------------------------------------------

    def _reset_hand(self) -> None:
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        for p in self.players:
            p.reset_for_hand()

    def _post_blinds(self) -> None:
        n = len(self.players)
        if n == 2:
            # Heads-up: dealer is SB
            self.sb_idx = self.dealer_idx
            self.bb_idx = (self.dealer_idx + 1) % n
        else:
            self.sb_idx = (self.dealer_idx + 1) % n
            self.bb_idx = (self.dealer_idx + 2) % n

        sb = self.players[self.sb_idx]
        bb = self.players[self.bb_idx]

        sb_posted = sb.bet(self.small_blind)
        self.pot += sb_posted
        self._log(f"{sb.name} posts small blind {sb_posted}")

        bb_posted = bb.bet(self.big_blind)
        self.pot += bb_posted
        self.current_bet = bb_posted
        self._log(f"{bb.name} posts big blind {bb_posted}")

    def _deal_hole_cards(self) -> None:
        for p in self.players:
            p.hole_cards = self.deck.deal(2)  # type: ignore[union-attr]

    def _deal_community(self, n: int, burn: bool = True) -> None:
        assert self.deck is not None
        if burn:
            self.deck.deal()  # burn card
        cards = self.deck.deal(n) if n > 1 else [self.deck.deal()]
        self.community_cards.extend(cards)

    # ------------------------------------------------------------------
    # Betting round
    # ------------------------------------------------------------------

    def _betting_round(self, stage: str) -> str:
        """Run one betting round.

        Returns 'all_fold' if everyone but one player folded,
        else 'continue'.
        """
        n = len(self.players)

        # Reset per-round bet counters for postflop streets
        if stage != 'preflop':
            self.current_bet = 0
            for p in self.players:
                p.current_bet = 0

        # Determine first player to act
        if stage == 'preflop':
            if n == 2:
                # Heads-up preflop: dealer/SB acts first
                start_idx = self.dealer_idx
            else:
                # UTG = player after BB
                start_idx = (self.bb_idx + 1) % n
        else:
            # Postflop: first active player left of dealer
            start_idx = (self.dealer_idx + 1) % n
            for _ in range(n):
                if not self.players[start_idx].folded:
                    break
                start_idx = (start_idx + 1) % n

        # visited_since_raise: indices of players who have acted since the
        # last raise (or since the start of the round)
        visited_since_raise: set[int] = set()

        current_idx = start_idx
        safety = n * (n + 6)  # prevents infinite loops in edge cases

        for _ in range(safety):
            # Termination check ─────────────────────────────────────────
            active = [
                (i, p) for i, p in enumerate(self.players)
                if not p.folded and not p.all_in
            ]
            if not active:
                break

            max_bet = max(p.current_bet for p in self.players if not p.folded)
            bets_equal = all(p.current_bet == max_bet for _, p in active)
            all_acted = all(i in visited_since_raise for i, _ in active)
            if bets_equal and all_acted:
                break
            # ────────────────────────────────────────────────────────────

            player = self.players[current_idx]

            if player.folded or player.all_in:
                current_idx = (current_idx + 1) % n
                continue

            to_call = max_bet - player.current_bet

            # Skip players who have already matched and acted
            if current_idx in visited_since_raise and to_call == 0:
                current_idx = (current_idx + 1) % n
                continue

            action, amount = self._get_action(player, to_call)
            visited_since_raise.add(current_idx)

            if action == 'fold':
                player.folded = True
                self._log(f"{player.name} folds")
                still_active = [p for p in self.players if not p.folded]
                if len(still_active) == 1:
                    return 'all_fold'

            elif action in ('check', 'call'):
                if to_call > 0:
                    actual = player.bet(to_call)
                    self.pot += actual
                    self._log(f"{player.name} calls {actual}")
                else:
                    self._log(f"{player.name} checks")

            elif action == 'raise':
                # amount = total chips to commit this action (>= to_call)
                commit = max(to_call, min(amount, player.chips))
                actual = player.bet(commit)
                self.pot += actual
                self.current_bet = player.current_bet
                self._log(f"{player.name} raises to {player.current_bet}")
                # Everyone else must act again
                visited_since_raise = {current_idx}

            current_idx = (current_idx + 1) % n

        return 'continue'

    # ------------------------------------------------------------------
    # Showdown
    # ------------------------------------------------------------------

    def _showdown(self) -> None:
        active = [p for p in self.players if not p.folded]

        if len(active) == 1:
            winner = active[0]
            winner.chips += self.pot
            self._log(f"\n{winner.name} wins {self.pot} (all others folded)")
            return

        self._log("\n--- Showdown ---")
        results: list[tuple[tuple, Player, tuple]] = []
        for p in active:
            score, combo = best_hand(p.hole_cards, self.community_cards)
            hole_str = self._cards_str(p.hole_cards)
            self._log(f"  {p.name}: {hole_str} → {hand_name(score)}")
            results.append((score, p, combo))

        results.sort(key=lambda x: x[0], reverse=True)
        best_score = results[0][0]
        winners = [(s, p, c) for s, p, c in results if s == best_score]

        split = self.pot // len(winners)
        remainder = self.pot % len(winners)

        for i, (_, p, _) in enumerate(winners):
            award = split + (remainder if i == 0 else 0)
            p.chips += award
            self._log(f"  {p.name} wins {award}")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _move_dealer(self) -> None:
        self.dealer_idx = (self.dealer_idx + 1) % len(self.players)

    def _log(self, msg: str) -> None:
        self.hand_log.append(msg)

    @staticmethod
    def _cards_str(cards: list) -> str:
        return ' '.join(str(c) for c in cards)
