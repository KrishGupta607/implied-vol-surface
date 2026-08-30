"""Fetch SPY option chains from Yahoo Finance as one tidy DataFrame."""

import numpy as np
import pandas as pd
import yfinance as yf

# Roughly log-spaced days to expiry. For each target we take the nearest listed
# expiry, so the ladder still spans a week to a year whenever this is rerun.
TARGET_DAYS = [7, 14, 30, 60, 90, 120, 180, 270, 365]


def pick_expiries(all_expiries, today):
    """Return the listed expiry closest to each entry in TARGET_DAYS."""
    dates = pd.to_datetime(list(all_expiries))

    chosen = []
    for target in TARGET_DAYS:
        nearest = min(dates, key=lambda d: abs((d - today).days - target))
        if nearest not in chosen:
            chosen.append(nearest)
    return chosen


def fetch_chain(ticker="SPY"):
    """Pull option chains and return one row per contract.

    Columns: expiry, T, type, strike, bid, ask, mid, spread, volume,
             openInterest, yf_iv, lastTradeDate, spot, snapshot

    T is calendar days to expiry divided by 365. yf_iv is Yahoo's own implied
    volatility, kept only as a benchmark to check our own solver against.
    """
    tk = yf.Ticker(ticker)

    # Time to expiry must be measured from the moment the QUOTES were set, not
    # from the calendar date the script happens to run. Over a weekend or after
    # hours those differ, and for a five-day contract a two-day error inflates
    # implied volatility by well over a point.
    history = tk.history(period="5d")
    today = history.index[-1].tz_localize(None).normalize()
    spot = float(history["Close"].iloc[-1])

    parts = []
    for expiry in pick_expiries(tk.options, today):
        chain = tk.option_chain(expiry.strftime("%Y-%m-%d"))

        calls = chain.calls.copy()
        calls["type"] = "C"
        calls["expiry"] = expiry

        puts = chain.puts.copy()
        puts["type"] = "P"
        puts["expiry"] = expiry

        parts.append(calls)
        parts.append(puts)

    df = pd.concat(parts, ignore_index=True)
    df = df.rename(columns={"impliedVolatility": "yf_iv"})

    df["T"] = (df["expiry"] - today).dt.days / 365
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df["spread"] = df["ask"] - df["bid"]
    df["spot"] = spot
    df["snapshot"] = today

    keep = ["expiry", "T", "type", "strike", "bid", "ask", "mid", "spread",
            "volume", "openInterest", "yf_iv", "lastTradeDate", "spot", "snapshot"]
    df = df[keep].sort_values(["expiry", "type", "strike"])
    return df.reset_index(drop=True)



# Filter settings. SIGMA_REF is only used to size the strike band -- it is a
# rough long-run volatility for SPY, not an estimate of anything we price with.
SIGMA_REF = 0.20
N_SIGMA = 3.0
MAX_REL_SPREAD = 0.25
MIN_T = 3 / 365


def clean_chain(df):
    """Drop contracts whose quotes carry no usable volatility signal.

    Six filters, each removing a different kind of unusable row. Returns a copy;
    the input frame is not modified.
    """
    out = df.copy()

    # A zero bid means nobody will pay anything, so the mid is not a price.
    has_bid = out["bid"] > 0

    # Crossed or locked quotes are stale-feed artifacts, not tradeable prices.
    two_sided = out["ask"] > out["bid"]

    # A quote a quarter of its own price wide has no meaningful midpoint.
    rel_spread = out["spread"] / out["mid"]
    tight_enough = rel_spread <= MAX_REL_SPREAD

    # Keep strikes within N_SIGMA typical moves of spot. The band widens with
    # sqrt(T), because a 30% move is impossible in a week and routine in a year.
    band = N_SIGMA * SIGMA_REF * np.sqrt(out["T"])
    log_moneyness = np.log(out["strike"] / out["spot"])
    near_money = log_moneyness.abs() <= band

    # Almost-expired options have near-zero vega, so inverting for sigma is
    # numerically unstable.
    not_expiring = out["T"] >= MIN_T

    # Somebody has to have traded it or be holding it.
    volume = out["volume"].fillna(0)
    open_interest = out["openInterest"].fillna(0)
    traded = (volume > 0) | (open_interest > 0)

    keep = (has_bid & two_sided & tight_enough
            & near_money & not_expiring & traded)

    out = out[keep].copy()
    out["log_moneyness"] = log_moneyness[keep]
    return out.reset_index(drop=True)


def keep_otm(df):
    """Keep out-of-the-money contracts only: puts below spot, calls above.

    They are almost pure time value, they are the liquid side of each strike,
    and they avoid the deep in-the-money region where an imperfect forward
    distorts implied volatility most. CBOE builds VIX the same way.
    """
    otm = (((df["type"] == "C") & (df["strike"] >= df["spot"]))
           | ((df["type"] == "P") & (df["strike"] < df["spot"])))
    return df[otm].reset_index(drop=True)


if __name__ == "__main__":
    raw = fetch_chain()
    clean = clean_chain(raw)
    print(f"{len(raw)} contracts -> {len(clean)} after cleaning "
          f"({100 * (1 - len(clean) / len(raw)):.1f}% dropped)")
    print(clean.groupby(["expiry", "type"]).size().unstack())
