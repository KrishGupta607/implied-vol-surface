# SPY Implied Volatility Surface

Building a volatility surface from SPY option chains: pulling live quotes, inverting
Black-Scholes numerically for implied volatility, and measuring where the model's
assumptions break.

![Implied volatility smile](figures/smile.png)

## The question

Black-Scholes prices an option from five inputs. Four of them — spot, strike, time to
expiry, and the interest rate — can be looked up. The fifth, volatility, cannot: it
describes the future and exists nowhere.

But the market publishes the *answer* — the option's price. So the equation can be run
backwards: given the price, solve for the volatility that produces it. That number is
the **implied volatility**, and it is the market's own estimate of how much SPY will
move, expressed in a unit everyone agrees on.

If Black-Scholes were literally true, a single volatility would price every contract on
SPY. It does not. **This project maps exactly how and where it fails.**

Snapshot: the close on Friday 28 August 2026, SPY at 769.35. 1,270 contracts across
nine expiries from 7 to 385 days.

## Findings

### 1. The volatility skew

Implied volatility falls steeply as strike rises. On the 28-day expiry:

| strike vs spot | implied volatility |
| --- | --- |
| 16% below | 28.6% |
| at the money | 11.9% |
| 10% above | 13.1% |

Same underlying, same 28 days, one contract per strike. Black-Scholes requires these to
be equal. The gap is the market pricing crash risk: real markets fall faster than a
lognormal distribution allows, and investors holding shares buy puts as insurance, which
is persistent one-directional demand at low strikes.

Short-dated expiries show a markedly steeper skew than long-dated ones, and the curves
cross around 12% below spot — near-term fear is concentrated in a crash scenario, while
long-dated volatility reflects general uncertainty growing with time.

### 2. The term structure is upward sloping

![Term structure](figures/term_structure.png)

At-the-money implied volatility rises monotonically from **9.7% at 7 days to 18.3% at
385 days** — the normal shape in a calm market, and it inverts under stress, when
near-term fear spikes above long-run expectations.

Interpolated onto standard tenors, in total variance rather than volatility (variance
accumulates roughly linearly in time; interpolating volatility directly can imply
negative variance over an interval, which is an arbitrage):

| tenor | 7d | 14d | 30d | 60d | 90d | 180d | 270d | 365d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM IV | 9.68% | 10.03% | 11.80% | 13.25% | 13.98% | 15.83% | 17.07% | 18.16% |

### 3. SPY's dividend, visible in the forward prices

Rather than assuming an interest rate and a dividend yield, the forward price for each
expiry is implied directly from put-call parity, using 989 matched call/put pairs.

| expiry | days | forward | F/S − 1 | implied yield |
| --- | --- | --- | --- | --- |
| 2026-09-04 | 7 | 769.75 | 0.05% | 1.29% |
| 2026-09-11 | 14 | 770.19 | 0.11% | 1.15% |
| 2026-09-25 | 28 | 769.56 | **0.03%** | **3.64%** |
| 2026-10-30 | 63 | 772.45 | 0.40% | 1.67% |
| 2026-11-30 | 94 | 775.16 | 0.75% | 1.08% |
| 2026-12-31 | 125 | 776.39 | 0.92% | 1.34% |
| 2027-03-19 | 203 | 783.15 | 1.79% | 0.80% |
| 2027-06-17 | 293 | 790.18 | 2.71% | 0.67% |
| 2027-09-17 | 385 | 797.61 | 3.67% | 0.58% |

Two things in that table point at the same event.

**The forward gap shrinks where it should grow.** Interest accumulates with time, so
`F/S − 1` should rise monotonically. It goes 0.05% at 7 days, 0.11% at 14 days, then
**back down to 0.03% at 28 days** — a longer maturity with a *smaller* gap. Something
subtracted value from that forward.

**The implied yield spikes, then decays.** 3.64% at 28 days, falling through 1.67%,
1.08%, 0.80% to 0.58% at 385 days.

Both are the dividend. SPY's last payment was 18 June 2026, so the next fell around
**18 September** — inside the 28-day window and every window after it. One discrete
payment of roughly $1.90 annualizes to `1.90 / (769.35 * 28/365) = 3.2%` over a 28-day
window, against 3.64% measured, and shrinks toward SPY's true ~1% annual yield as the
window lengthens.

The implied yields at 7 and 14 days are noisy rather than meaningful: `ln(F/S)` is tiny
at short maturities and dividing it by a tiny `T` amplifies any quote noise.

Using the implied forward rather than an assumed dividend yield also matters for
internal consistency. A flat assumed yield makes calls and puts at the same strike imply
different volatilities, leaving a visible discontinuity in the smile at the money of up
to **1.1 volatility points** — put-call parity says a call and a put at one strike must
imply the same volatility, so that gap measures how wrong the assumed forward is. The
implied forward closes it to a maximum of **0.32 points**, and leaves no contract
unsolvable.

### 4. Options were priced above what SPY delivered

![Implied versus realized volatility](figures/implied_vs_realized.png)

| horizon | implied | realized | premium |
| --- | --- | --- | --- |
| 7d | 9.68% | 6.26% | +3.42 |
| 14d | 10.03% | 7.83% | +2.20 |
| 28d | 11.58% | 9.52% | +2.06 |
| 63d | 13.32% | 11.24% | +2.08 |
| 94d | 14.04% | 13.53% | +0.51 |
| 125d | 14.67% | 12.80% | +1.87 |
| 203d | 16.11% | 13.72% | +2.39 |
| 293d | 17.29% | 13.18% | +4.11 |
| 385d | 18.34% | 12.64% | +5.70 |

Implied exceeds realized at **every one of nine horizons**, mean **+2.70 volatility
points**. This is the variance risk premium: option sellers act as insurers and are paid
more than the average claim, in compensation for carrying the risk of large moves.

**Caveat, stated plainly:** this compares forward-looking implied volatility against
*trailing* realized volatility over a matched lookback. A strict test would compare
implied volatility at a moment against what happened *afterwards*, which requires
waiting rather than measuring.

## Method

```
Yahoo Finance
     |  3,246 quoted contracts across 9 expiries
     v
fetch_chain        9 expiries sampled by a rule targeting 7/14/30/60/90/120/180/270/365
     |             days; T, mid and spread computed
     v
clean_chain        six quality filters                            ->  2,290
     |
     v
implied_forwards   put-call parity -> one forward per expiry
     |
     v
keep_otm           out-of-the-money contracts only                ->  1,270
     |
     v
add_implied_vol    bisection on Black-Scholes -> sigma per contract
     |
     v
data/surface.csv   ->  plots.py, realized.py, term_structure.py
```

`implied_forwards` must run before `keep_otm`, because parity needs matched call/put
pairs at the same strike and `keep_otm` keeps only one side of each.

### Time to expiry is measured from the quote, not from the clock

`T` is taken from the date of the last close, not from the calendar date the script
runs. Over a weekend or after hours these differ, and the difference is not small:
Friday's frozen quotes read on a Sunday would measure a 7-day contract as 5 days, and
the solver compensates with volatility it should not need — worth **1.7 points** at the
shortest expiry, and enough to distort the near end of the term structure. Two days is
negligible at 385 days and decisive at 7. Measuring from the quote date also produces
closer agreement with Yahoo's own implied volatility.

### Inverting for implied volatility

Volatility cannot be isolated algebraically — it sits inside the normal CDF twice, which
has no elementary inverse. So the solver searches.

**Bisection**, bracketing sigma in [0.001, 5.0] and halving until the bracket is narrower
than 1e-6 — about 23 iterations. It is safe because **option price is strictly
increasing in volatility**, which guarantees exactly one solution and tells the search
which direction to step.

Newton's method, using vega as the slope, converges in roughly 4 iterations instead of
23, but can diverge where vega approaches zero — precisely the deep in-the-money and far
out-of-the-money contracts. At this scale reliability is worth more than speed.

The solver returns `NaN` when no volatility in the bracket can reproduce the observed
price, rather than silently returning a bracket boundary.

### Data quality

Roughly 30% of quoted contracts carry no usable volatility signal. The solver never
refuses a bad quote — it returns a plausible-looking number — so filtering is the only
defence.

| filter | fails alone | additional cut | reason |
| --- | --- | --- | --- |
| `bid > 0` | 176 | 176 | no bid means the mid is not a price |
| `ask > bid` | 62 | 0 | crossed quotes are feed artifacts |
| `spread / mid <= 0.25` | 361 | 185 | a quote a quarter of its own width has no midpoint |
| `abs(ln(K/S)) <= 3 * sigma * sqrt(T)` | 771 | 539 | strikes beyond reach carry no signal |
| `T >= 3/365` | 0 | 0 | near-expiry vega collapses |
| `volume > 0 or OI > 0` | 93 | 56 | somebody must trade or hold it |

**2,290 of 3,246 kept (70.5%).**

The moneyness band scales with `sqrt(T)` rather than being a fixed percentage. A strike
10% below spot sits 3.6 typical moves away at 7 days — priced at zero, unreachable — but
only 0.5 typical moves at 385 days, where it trades actively and is worth $21.84. The
same percentage means entirely different things at different maturities.

Prices are bid/ask **midpoints**, never last traded price: last trades can be days stale
(one raw row had not traded in eight days) and execute at the bid or the ask rather than
in the middle.

Out-of-the-money contracts only — puts below spot, calls above. They are almost pure
time value, they are the liquid side of each strike, and they avoid the deep
in-the-money region where any residual forward error is amplified. CBOE constructs VIX
the same way.

### Put-call parity as a data check

989 matched call/put pairs, comparing each deviation from parity against what the quotes
themselves allow — a mid price can be off by half the bid-ask spread on each leg, so the
two-leg trade has a noise budget of half the combined spread.

| | value |
| --- | --- |
| median absolute violation | $0.560 |
| median noise budget | $1.655 |
| pairs deviating beyond quote noise | 20.1% |

**Roughly 80% of apparent parity violations are smaller than the bid-ask spread**, so
they are quote noise rather than opportunity — crossing the spread would cost more than
the deviation is worth. This is why the comparison has to be against the spread rather
than against zero.

## Validation

**Against the vendor.** Yahoo publishes its own implied volatility, kept as `yf_iv` for
comparison and never used as an input. Median difference **−0.0024**, with 54.2% of
contracts within 0.01. The residual is consistent with Yahoo pricing off stale last-trade
prices rather than midpoints.

**Against VIX.** At-the-money 30-day implied volatility is 11.80%, against a published
VIX of 14.43%. That gap is not an error: VIX is not an at-the-money measure but a
variance-swap calculation integrating every out-of-the-money strike, weighted by
`1 / K^2`, which puts the most weight on the low strikes — exactly where the skew makes
volatility highest. Recomputing VIX's way from this project's own chain gives **13.40%**.

| | value |
| --- | --- |
| our at-the-money, 30d | 11.80% |
| our VIX-style calculation | 13.40% |
| published VIX | 14.43% |

The remaining 1.0 point is explained by VIX being written on SPX rather than SPY,
blending two expiries around 30 days rather than using one, and an approximate strike
weighting and truncation rule.

## Limitations

- **American options priced with a European model.** SPY options are American;
  Black-Scholes prices European. This is a standard approximation for SPY — early
  exercise is only meaningfully valuable around dividend dates and for deep
  in-the-money puts — but SPX options would be the rigorous choice.
- **A single snapshot**, the close on Friday 28 August 2026. Nothing here describes how
  the surface evolves.
- **Free vendor data.** Yahoo quotes, not exchange data, with imprecise timestamps.
- **A flat 4% risk-free rate**, rather than a Treasury yield matched to each maturity.
  The forward is implied from parity, which absorbs much of this, but not the
  discounting.
- **Term structure sampled at listed expiries**, so points sit at 203 days rather than
  180. Fine for one snapshot; comparing surfaces across days would require interpolating
  onto a fixed grid first, which `term_structure.py` does.
- **Implied is compared against trailing realized volatility**, as noted above.

## Next steps

- Fit a smooth, arbitrage-free surface (SVI, or a spline in log-moneyness and total
  variance) rather than plotting raw points.
- Repeat the pull daily and study how the surface moves, instead of one snapshot.
- Compare implied volatility against *subsequently* realized volatility to measure the
  variance risk premium properly.
- Use a maturity-matched Treasury curve instead of a flat rate.

## Repository

```
src/
  black_scholes.py    call/put pricing with a dividend yield; bisection IV solver
  data.py             fetch chains, six quality filters, out-of-the-money filter
  forward.py          forward implied from put-call parity; parity violation check
  build_surface.py    the pipeline; writes data/surface.csv
  term_structure.py   at-the-money curve, fixed-tenor interpolation, VIX-style vol
  plots.py            smile and term structure figures
  realized.py         realized volatility and the implied/realized comparison
  style.py            shared chart styling

data/surface.csv      1,270 contracts, 9 expiries, snapshot 2026-08-28
figures/              smile, term structure, implied vs realized
```

## Running it

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

.venv/Scripts/python.exe src/build_surface.py    # fetch, clean, solve, save
.venv/Scripts/python.exe src/plots.py            # smile and term structure
.venv/Scripts/python.exe src/realized.py         # implied vs realized
.venv/Scripts/python.exe src/term_structure.py   # tenor grid and VIX check
```

Python 3.13, with numpy, pandas, scipy, matplotlib and yfinance.
