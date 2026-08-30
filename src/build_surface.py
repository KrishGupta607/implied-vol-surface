"""Build the implied volatility surface and save it to data/surface.csv."""

from pathlib import Path

import pandas as pd

from black_scholes import implied_vol
from data import fetch_chain, clean_chain, keep_otm
from forward import implied_forwards, parity_violations, effective_dividend_yield

RISK_FREE = 0.04
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "surface.csv"


def add_implied_vol(df, r=RISK_FREE):
    """Solve for each contract's implied volatility and add it as a column.

    A plain loop: bisection needs a different number of steps per contract, so
    this cannot be vectorized the way the pricing functions can.
    """
    solved = []
    for row in df.itertuples():
        solved.append(implied_vol(row.mid, row.spot, row.strike, row.T,
                                  r, row.type, row.q_eff))

    out = df.copy()
    out["iv"] = solved
    return out


if __name__ == "__main__":
    raw = fetch_chain()
    clean = clean_chain(raw)

    forwards, pairs = implied_forwards(clean, RISK_FREE)
    checked = parity_violations(pairs, RISK_FREE)

    print("--- implied forward per expiry ---")
    print(f"{'expiry':12s} {'days':>5s} {'spot':>8s} {'forward':>9s} {'F/S-1':>8s} {'q_eff':>7s}")
    for expiry, group in clean.groupby("expiry"):
        T = group["T"].iloc[0]
        spot = group["spot"].iloc[0]
        F = forwards[expiry]
        q = effective_dividend_yield(F, spot, T, RISK_FREE)
        print(f"{expiry.date()!s:12s} {round(T*365):5d} {spot:8.2f} {F:9.2f} "
              f"{100*(F/spot-1):7.2f}% {100*q:6.2f}%")

    beyond = checked["beyond_noise"].mean()
    print(f"\n--- put-call parity ---")
    print(f"{len(checked)} matched call/put pairs")
    print(f"median absolute violation: ${checked['violation'].abs().median():.3f}")
    print(f"median noise budget (half combined spread): ${checked['noise_budget'].median():.3f}")
    print(f"pairs violating parity beyond quote noise: {100*beyond:.1f}%")

    otm = keep_otm(clean).copy()
    otm["F"] = otm["expiry"].map(forwards)
    otm["q_eff"] = effective_dividend_yield(otm["F"], otm["spot"], otm["T"], RISK_FREE)

    df = add_implied_vol(otm)
    failed = df["iv"].isna().sum()
    print(f"\n{len(df)} contracts, {failed} unsolvable ({100 * failed / len(df):.1f}%)")

    ok = df.dropna(subset=["iv"])
    diff = ok["iv"] - ok["yf_iv"]
    print(f"our iv vs yahoo's: median {diff.median():+.4f}, "
          f"within 0.01: {(diff.abs() < 0.01).mean() * 100:.1f}%")

    OUT_PATH.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nsaved {len(df)} rows to {OUT_PATH.relative_to(Path.cwd())}")
