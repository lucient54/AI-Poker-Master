"""Texas Hold'em game-state engine.

Tracks players, blinds, pot, community cards and betting across all four
streets (preflop → flop → turn → river → showdown).
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Sequence

from .card import Card, Deck
from .hand_evaluator import HAND_RANK_NAMES, HandRank, evaluate_hand


class GameStage(Enum):
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()


class PlayerAction(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


class Player:
    """Represents one seat at the table."""

    def __init__(self, name: str, stack: float = 1_000, is_ai: bool = False) -> None:
        self.name = name
        self.stack = stack
        self.is_ai = is_ai
        self.hole_cards: list[Card] = []
        self.is_folded = False
        self.is_all_in = False
        self.current_bet: float = 0.0

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.is_folded = False
        self.is_all_in = False
        self.current_bet = 0.0

    def __repr__(self) -> str:  # pragma: no cover
        return f"Player({self.name!r}, stack={self.stack})"


class TexasHoldemGame:
    """Manages a single table of Texas Hold'em.

    Supports unlimited number of players (≥ 2).  The caller is responsible
    for acting on each player in turn by calling :meth:`apply_action`.
    """

    def __init__(
        self,
        players: list[Player],
        small_blind: float = 10,
        big_blind: float = 20,
    ) -> None:
        if len(players) < 2:
            raise ValueError("At least 2 players are required.")
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.dealer_pos: int = 0

        # State reset at the start of each hand
        self.deck: Deck | None = None
        self.community_cards: list[Card] = []
        self.pot: float = 0.0
        self.current_bet: float = 0.0
        self.stage: GameStage = GameStage.PREFLOP
        self.hand_history: list[str] = []

    # ------------------------------------------------------------------
    # Hand lifecycle
    # ------------------------------------------------------------------

    def start_hand(self) -> bool:
        """Set up a new hand.  Returns ``False`` if fewer than 2 players have chips."""
        active = [p for p in self.players if p.stack > 0]
        if len(active) < 2:
            return False

        self.deck = Deck()
        self.community_cards = []
        self.pot = 0.0
        self.current_bet = 0.0
        self.stage = GameStage.PREFLOP
        self.hand_history = []

        for p in self.players:
            p.reset_for_hand()

        # Post blinds
        sb_pos = (self.dealer_pos + 1) % len(self.players)
        bb_pos = (self.dealer_pos + 2) % len(self.players)
        self._post_blind(self.players[sb_pos], self.small_blind)
        self._post_blind(self.players[bb_pos], self.big_blind)
        self.current_bet = self.big_blind

        # Deal 2 hole cards to each player with chips
        for _ in range(2):
            for p in self.players:
                if p.stack >= 0 and not p.is_folded:
                    p.hole_cards.extend(self.deck.deal(1))

        return True

    def deal_flop(self) -> None:
        assert self.deck is not None
        self.community_cards.extend(self.deck.deal(3))
        self.stage = GameStage.FLOP
        self._reset_betting()

    def deal_turn(self) -> None:
        assert self.deck is not None
        self.community_cards.extend(self.deck.deal(1))
        self.stage = GameStage.TURN
        self._reset_betting()

    def deal_river(self) -> None:
        assert self.deck is not None
        self.community_cards.extend(self.deck.deal(1))
        self.stage = GameStage.RIVER
        self._reset_betting()

    def advance_stage(self) -> None:
        """Deal the next street automatically."""
        if self.stage == GameStage.PREFLOP:
            self.deal_flop()
        elif self.stage == GameStage.FLOP:
            self.deal_turn()
        elif self.stage == GameStage.TURN:
            self.deal_river()
        elif self.stage == GameStage.RIVER:
            self.stage = GameStage.SHOWDOWN

    # ------------------------------------------------------------------
    # Betting
    # ------------------------------------------------------------------

    def apply_action(
        self, player: Player, action: PlayerAction, amount: float = 0
    ) -> None:
        """Apply *action* for *player* and update pot / bet state."""
        if action == PlayerAction.FOLD:
            player.is_folded = True
            self.hand_history.append(f"{player.name}: fold")

        elif action == PlayerAction.CHECK:
            self.hand_history.append(f"{player.name}: check")

        elif action == PlayerAction.CALL:
            to_call = min(self.current_bet - player.current_bet, player.stack)
            player.stack -= to_call
            player.current_bet += to_call
            self.pot += to_call
            self.hand_history.append(f"{player.name}: call {to_call:.0f}")

        elif action in (PlayerAction.BET, PlayerAction.RAISE):
            increase = amount - player.current_bet
            actual = min(increase, player.stack)
            player.stack -= actual
            player.current_bet += actual
            self.pot += actual
            self.current_bet = max(self.current_bet, player.current_bet)
            self.hand_history.append(f"{player.name}: {action.value} {player.current_bet:.0f}")

        elif action == PlayerAction.ALL_IN:
            all_in = player.stack
            player.current_bet += all_in
            player.stack = 0.0
            player.is_all_in = True
            self.pot += all_in
            if player.current_bet > self.current_bet:
                self.current_bet = player.current_bet
            self.hand_history.append(f"{player.name}: all-in {all_in:.0f}")

    # ------------------------------------------------------------------
    # Showdown
    # ------------------------------------------------------------------

    def determine_winners(self) -> list[tuple[Player, float, str]]:
        """Evaluate hands and award the pot; returns a list of ``(player, chips_won, hand_name)``."""
        active = [p for p in self.players if not p.is_folded]

        if len(active) == 1:
            active[0].stack += self.pot
            return [(active[0], self.pot, "last player standing")]

        hand_results = [
            (p, evaluate_hand(p.hole_cards + self.community_cards)) for p in active
        ]
        hand_results.sort(key=lambda x: x[1], reverse=True)
        best = hand_results[0][1]
        winners = [(p, res) for p, res in hand_results if res == best]

        split = self.pot / len(winners)
        self.stage = GameStage.SHOWDOWN
        result: list[tuple[Player, float, str]] = []
        for p, res in winners:
            p.stack += split
            result.append((p, split, HAND_RANK_NAMES.get(res[0], "Unknown")))

        self.dealer_pos = (self.dealer_pos + 1) % len(self.players)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _post_blind(self, player: Player, amount: float) -> None:
        actual = min(amount, player.stack)
        player.stack -= actual
        player.current_bet = actual
        self.pot += actual

    def _reset_betting(self) -> None:
        self.current_bet = 0.0
        for p in self.players:
            p.current_bet = 0.0

    def active_players(self) -> list[Player]:
        """Players still in the hand (not folded, not all-in)."""
        return [p for p in self.players if not p.is_folded and not p.is_all_in]

    def call_amount_for(self, player: Player) -> float:
        """How much *player* must put in to call the current bet."""
        return max(0.0, self.current_bet - player.current_bet)
