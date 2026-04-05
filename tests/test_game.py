"""Tests for the Texas Hold'em game engine."""
import pytest
from poker.game import GameStage, Player, PlayerAction, TexasHoldemGame


def make_game(n: int = 3, stack: int = 1_000) -> TexasHoldemGame:
    players = [Player(f"P{i}", stack=stack) for i in range(n)]
    return TexasHoldemGame(players, small_blind=10, big_blind=20)


class TestGameSetup:
    def test_requires_at_least_two_players(self):
        with pytest.raises(ValueError):
            TexasHoldemGame([Player("solo")])

    def test_start_hand_deals_two_hole_cards(self):
        g = make_game()
        assert g.start_hand()
        for p in g.players:
            assert len(p.hole_cards) == 2

    def test_blinds_posted(self):
        g = make_game()
        g.start_hand()
        # SB + BB = 10 + 20 = 30
        assert g.pot == 30

    def test_stacks_reduced_by_blinds(self):
        g = make_game(stack=1_000)
        g.start_hand()
        stacks = [p.stack for p in g.players]
        # P0 is dealer; P1 posts SB=10, P2 posts BB=20
        assert stacks[1] == 990
        assert stacks[2] == 980

    def test_returns_false_when_only_one_player_has_chips(self):
        players = [Player("rich", stack=1_000), Player("broke", stack=0)]
        g = TexasHoldemGame(players)
        assert not g.start_hand()


class TestBetting:
    def test_call_action(self):
        g = make_game()
        g.start_hand()
        hero = g.players[0]
        before = hero.stack
        g.apply_action(hero, PlayerAction.CALL)
        # Hero must call up to current_bet (20) minus any already posted
        assert hero.stack <= before

    def test_fold_marks_player(self):
        g = make_game()
        g.start_hand()
        hero = g.players[0]
        g.apply_action(hero, PlayerAction.FOLD)
        assert hero.is_folded

    def test_check_does_not_change_stack(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        hero = g.players[0]
        before = hero.stack
        g.apply_action(hero, PlayerAction.CHECK)
        assert hero.stack == before

    def test_bet_increases_pot(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        hero = g.players[0]
        pot_before = g.pot
        g.apply_action(hero, PlayerAction.BET, amount=50)
        assert g.pot > pot_before

    def test_raise_updates_current_bet(self):
        g = make_game()
        g.start_hand()
        hero = g.players[0]
        g.apply_action(hero, PlayerAction.RAISE, amount=60)
        assert g.current_bet == 60

    def test_all_in(self):
        g = make_game(stack=100)
        g.start_hand()
        hero = g.players[0]
        g.apply_action(hero, PlayerAction.ALL_IN)
        assert hero.stack == 0
        assert hero.is_all_in


class TestStreets:
    def test_deal_flop_gives_three_cards(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        assert len(g.community_cards) == 3
        assert g.stage == GameStage.FLOP

    def test_deal_turn_gives_four_cards(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        g.deal_turn()
        assert len(g.community_cards) == 4

    def test_deal_river_gives_five_cards(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        g.deal_turn()
        g.deal_river()
        assert len(g.community_cards) == 5

    def test_advance_stage_sequence(self):
        g = make_game()
        g.start_hand()
        assert g.stage == GameStage.PREFLOP
        g.advance_stage()
        assert g.stage == GameStage.FLOP
        g.advance_stage()
        assert g.stage == GameStage.TURN
        g.advance_stage()
        assert g.stage == GameStage.RIVER
        g.advance_stage()
        assert g.stage == GameStage.SHOWDOWN


class TestShowdown:
    def test_last_player_wins_pot(self):
        g = make_game()
        g.start_hand()
        pot = g.pot
        # Fold all but one
        for p in g.players[1:]:
            g.apply_action(p, PlayerAction.FOLD)
        winners = g.determine_winners()
        assert len(winners) == 1
        assert winners[0][1] == pot

    def test_winner_stack_increases(self):
        g = make_game()
        g.start_hand()
        for p in g.players[1:]:
            g.apply_action(p, PlayerAction.FOLD)
        winner = g.players[0]
        stack_before = winner.stack
        g.determine_winners()
        assert winner.stack > stack_before

    def test_showdown_with_full_board(self):
        g = make_game()
        g.start_hand()
        g.deal_flop()
        g.deal_turn()
        g.deal_river()
        winners = g.determine_winners()
        assert len(winners) >= 1
        for p, chips, _ in winners:
            assert chips > 0

    def test_chips_conserved_at_showdown(self):
        g = make_game(n=2, stack=1_000)
        g.start_hand()
        total_before = sum(p.stack for p in g.players) + g.pot
        g.deal_flop()
        g.deal_turn()
        g.deal_river()
        g.determine_winners()
        total_after = sum(p.stack for p in g.players)
        assert total_after == pytest.approx(total_before)
