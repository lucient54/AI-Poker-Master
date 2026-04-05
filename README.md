# AI Poker Master

A Texas Hold'em AI advisor that calculates pot odds, estimates hand equity
via Monte Carlo simulation, and recommends the optimal action (fold / check /
call / bet / raise) for any given situation.

---

## Features

| Module | What it does |
|---|---|
| `poker/card.py` | `Card`, `Deck`, `Rank`, `Suit` — full 52-card deck |
| `poker/hand_evaluator.py` | Evaluates the best 5-card hand from 5–7 cards (Royal Flush → High Card), handles wheel straights and tiebreakers |
| `poker/calculator.py` | Monte Carlo equity simulation, pot-odds, implied-odds and EV calculations |
| `poker/ai.py` | `PokerAI` decision engine — preflop hand-strength tables + postflop Monte Carlo, with tunable `aggression` and `tightness` |
| `poker/game.py` | `TexasHoldemGame` — full game-state engine: blinds, betting, street advancement, showdown |
| `main.py` | Interactive CLI hand advisor |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the interactive advisor
python main.py
```

### Card format

```
Rank + Suit   e.g.  Ah  Kd  Tc  9s  2h
Ranks: 2-9  T(ten)  J  Q  K  A
Suits: c(clubs)  d(diamonds)  h(hearts)  s(spades)
```

---

## Example output

```
  Hole   : Kh Qd
  Board  : Kd 7s 2c
  Hand   : One Pair

  ── STATISTICS ──────────────────────────────────────
  Equity vs 1 opponent(s) : 87.6%
  Position-adjusted equity  : 87.6%
  Pot size                  : 80
  Call amount               : 30
  Pot odds (break-even eq.) : 27.3%
  Expected value            : +66.4 chips

  ── RECOMMENDATION ──────────────────────────────────
  Action : RAISE  142

  ── REASONING ───────────────────────────────────────
  Raising to 142: One Pair equity 87.6% exceeds raise threshold 64.0%.
```

---

## AI Strategy

The AI combines two approaches used by professional poker solvers:

1. **Preflop hand-strength tables** — starting-hand ratings derived from the
   Chen formula and GTO hand-chart research, with a suited-hand bonus.
2. **Monte Carlo equity simulation** (postflop) — thousands of random runouts
   are sampled to estimate the hero's win probability against opponent ranges.

Decision thresholds adapt to two tunable parameters:

* `aggression` (0–1) — controls bet/raise sizing and frequency.
* `tightness` (0–1) — controls how selectively marginal hands are played.

```python
from poker.card import Card
from poker.ai import PokerAI, PokerPosition

ai = PokerAI(name="MyBot", aggression=0.7, tightness=0.6)

hole  = [Card.from_string("Ah"), Card.from_string("Ad")]
board = [Card.from_string("As"), Card.from_string("Kd"), Card.from_string("7h")]

print(ai.analyze_hand(hole, board, call_amount=50, pot_size=200,
                       num_opponents=2, position=PokerPosition.LATE))
```

---

## Running Tests

```bash
pytest tests/ -v
```

91 tests cover card parsing, hand evaluation (all hand ranks + tiebreakers),
pot-odds/EV functions, Monte Carlo equity accuracy, AI decisions, and the
full game engine.
