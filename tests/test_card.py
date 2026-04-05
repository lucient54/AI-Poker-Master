"""Tests for Card, Deck, Rank, Suit."""
import pytest
from poker.card import Card, Deck, Rank, Suit


def test_card_repr():
    assert repr(Card(14, 2)) == "Ah"
    assert repr(Card(13, 1)) == "Kd"
    assert repr(Card(10, 0)) == "Tc"


def test_card_from_string_basic():
    c = Card.from_string("Ah")
    assert c.rank == Rank.ACE
    assert c.suit == Suit.HEARTS


def test_card_from_string_ten():
    c = Card.from_string("Td")
    assert c.rank == Rank.TEN


def test_card_from_string_lowercase_rank():
    assert Card.from_string("ah").rank == Rank.ACE
    assert Card.from_string("kS").rank == Rank.KING


def test_card_from_string_invalid():
    with pytest.raises(ValueError):
        Card.from_string("XX")
    with pytest.raises(ValueError):
        Card.from_string("A")


def test_card_equality():
    assert Card.from_string("Ah") == Card.from_string("Ah")
    assert Card.from_string("Ah") != Card.from_string("As")


def test_card_hashable():
    s = {Card.from_string("Ah"), Card.from_string("Kd")}
    assert len(s) == 2


def test_deck_has_52_cards():
    d = Deck()
    assert len(d) == 52


def test_deck_deal():
    d = Deck()
    cards = d.deal(5)
    assert len(cards) == 5
    assert len(d) == 47


def test_deck_deal_too_many():
    d = Deck()
    with pytest.raises(ValueError):
        d.deal(53)


def test_deck_remove():
    d = Deck()
    known = [Card.from_string("Ah"), Card.from_string("Kd")]
    d.remove(known)
    assert len(d) == 50
    assert Card.from_string("Ah") not in d.cards


def test_deck_no_duplicates():
    d = Deck()
    assert len(set(d.cards)) == 52
