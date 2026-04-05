# AI-Poker-Master

A Texas Hold'em engine with a pot-odds AI that can be **played interactively**
or run in **self-play training mode** to generate hand-history data for model training.

---

## Features

| Feature | Description |
|---|---|
| Full game engine | Preflop → Flop → Turn → River → Showdown with correct betting rounds |
| Hand evaluator | Compares all C(7,5) = 21 five-card combos to find the best hand |
| Monte Carlo equity | Estimates your win probability by simulating thousands of run-outs |
| Pot-odds AI | Folds when equity < pot odds, calls when marginal, raises when strong |
| Interactive play | Human vs AI with live equity display each decision |
| Training mode | AI vs AI self-play with JSONL hand-history export |

---

## Quick start

```bash
# Requirements: Python 3.10+
python main.py                        # 1v1 vs AI, 1000 chips each
python main.py --players 4            # 3 AI opponents
python main.py --players 3 --chips 500 --hands 20   # 20-hand session

python train.py                       # 3 AIs, 1 000 hands
python train.py --hands 5000 --players 4 --out data.jsonl   # save records
```

---

## Play commands

During your turn you will see your hole cards, community cards, current pot,
and a live equity estimate. Enter one of:

| Command | Meaning |
|---|---|
| `check` | Pass (only when there is nothing to call) |
| `call` | Match the current bet |
| `fold` | Discard your hand |
| `raise <amount>` | Bet more than the current bet (e.g. `raise 80`) |

---

## Project structure

```
poker/
  card.py            Card and Deck classes
  hand_evaluator.py  7-card hand evaluator (all 21 five-card combos)
  odds_calculator.py Monte Carlo equity + pot-odds formula
  player.py          Player state (chips, hole cards, bet tracking)
  ai_agent.py        Pot-odds AI decision engine
  game.py            TexasHoldem base class (betting-round state machine)
main.py              Interactive human-vs-AI entry point
train.py             Self-play training / data generation entry point
```

---

## AI decision logic

```
equity  = monte_carlo_equity(hole_cards, community, num_opponents, simulations=600)
needed  = call_amount / (pot + call_amount)   # pot odds breakeven

if bluff_roll < bluff_rate:      raise (bluff)
elif equity > needed + margin:   raise (value bet, with probability = aggression)
elif equity >= needed:           call / check
else:                            fold / check
```

The training mode creates agents with different aggression/bluff personalities so
the dataset contains a variety of playing styles.

---

## Training output format (JSONL)

Each line is a JSON object:

```json
{
  "hand_number": 42,
  "community": ["T♠", "7♥", "2♦", "K♣", "9♠"],
  "players": [
    {"name": "AI-1", "hole_cards": ["A♠", "K♥"], "chips_before": 9800,
     "chips_after": 10250, "profit": 450, "folded": false},
    ...
  ]
}
```
