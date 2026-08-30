"""Imply each expiry's forward price from put-call parity.

Put-call parity is a no-arbitrage identity, true regardless of any pricing
model, because a call minus a put has the same payoff as the forward itself:

    C - P = exp(-r*T) * (F - K)

Rearranged, every matched call/put pair at the same strike gives an estimate
of F, the price the market expects the underlying to have at expiry:

    F = K + exp(r*T) * (C - P)

Using that F instead of assuming a risk-free rate and a dividend yield removes
the systematic error that otherwise makes calls and puts at the same strike
imply different volatilities.
"""

import numpy as np
import pandas as pd

# Only pairs this close to spot are used to fit F -- they are the liquid ones.
FIT_BAND = 0.05


def pair_up(df):
    """Match calls to puts at the same expiry and strike."""
    calls = df[df["type"] == "C"][["expiry", "T", "strike", "spot", "mid", "spread"]]
    puts = df[df["type"] == "P"][["expiry", "strike", "mid", "spread"]]
    return calls.merge(puts, on=["expiry", "strike"], suffixes=("_c", "_p"))


def implied_forwards(df, r):
    """Return one forward price per expiry, plus the pair table used to fit it."""
    pairs = pair_up(df)
    pairs["log_moneyness"] = np.log(pairs["strike"] / pairs["spot"])
    pairs["F_pair"] = pairs["strike"] + np.exp(r * pairs["T"]) * (pairs["mid_c"] - pairs["mid_p"])

    forwards = {}
    for expiry, group in pairs.groupby("expiry"):
        near = group[group["log_moneyness"].abs() <= FIT_BAND]
        if len(near) < 3:
            near = group.reindex(group["log_moneyness"].abs().sort_values().index).head(5)
        forwards[expiry] = float(near["F_pair"].median())

    pairs["F_fit"] = pairs["expiry"].map(forwards)
    return forwards, pairs


def parity_violations(pairs, r):
    """How far each pair deviates from parity, against what the quotes allow.

    A mid price can be off by half the bid-ask spread in either direction, so
    the two-leg trade has a noise budget of half the combined spread. Anything
    inside that is a quote artifact; anything outside is a genuine deviation.
    """
    out = pairs.copy()
    predicted = np.exp(-r * out["T"]) * (out["F_fit"] - out["strike"])
    out["violation"] = (out["mid_c"] - out["mid_p"]) - predicted
    out["noise_budget"] = 0.5 * (out["spread_c"] + out["spread_p"])
    out["beyond_noise"] = out["violation"].abs() > out["noise_budget"]
    return out


def effective_dividend_yield(forward, spot, T, r):
    """Convert a forward price into the dividend yield that would produce it.

    F = S * exp((r - q) * T)  ->  q = r - ln(F / S) / T

    This lets the existing pricing functions consume the market's forward
    without needing a separate forward-based pricer.
    """
    return r - np.log(forward / spot) / T
