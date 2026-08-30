"""At-the-money volatility term structure, on a fixed tenor grid.

The exchange lists expiries where it likes, so the measured curve sits at
whatever maturities happen to exist -- 201 days rather than 180, for example.
That is fine for one snapshot, but it means two snapshots taken on different
days cannot be stacked, and nothing can be compared against a published figure
like VIX, which is defined at exactly 30 days.

The fix is to interpolate onto a fixed grid. The interpolation is done in
TOTAL VARIANCE rather than in volatility:

    total variance   w = sigma^2 * T

Variance accumulates roughly linearly with time, so a straight line between two
points in w is a reasonable curve. Volatility does not, and interpolating it
directly can imply negative variance over an interval, which is an arbitrage.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SURFACE = ROOT / "data" / "surface.csv"

# The maturities volatility is conventionally quoted at, in days.
TENORS = [7, 14, 30, 60, 90, 180, 270, 365]


def atm_iv(group):
    """Implied volatility at the money, interpolated to log-moneyness zero."""
    g = group.sort_values("log_moneyness")
    return float(np.interp(0.0, g["log_moneyness"], g["iv"]))


def atm_curve(surface):
    """One row per expiry: the measured at-the-money volatility."""
    rows = []
    for expiry, group in surface.groupby("expiry"):
        T = float(group["T"].iloc[0])
        rows.append({"expiry": expiry, "days": round(T * 365), "T": T,
                     "atm_iv": atm_iv(group)})
    return pd.DataFrame(rows).sort_values("T").reset_index(drop=True)


def interpolate_tenors(curve, tenors=TENORS):
    """Interpolate the measured curve onto fixed tenors, via total variance.

    Returns NaN for any tenor outside the measured range rather than
    extrapolating, since a flat extension past the last expiry is a guess.
    """
    T_measured = curve["T"].to_numpy()
    w_measured = (curve["atm_iv"].to_numpy() ** 2) * T_measured

    rows = []
    for days in tenors:
        T = days / 365
        if T < T_measured.min() or T > T_measured.max():
            iv = np.nan
        else:
            w = np.interp(T, T_measured, w_measured)
            iv = np.sqrt(w / T)
        rows.append({"days": days, "T": T, "atm_iv": iv})

    return pd.DataFrame(rows)



def vix_style_vol(surface, expiry, r=0.04):
    """Variance-swap volatility for one expiry, computed the way VIX is.

    VIX is not at-the-money volatility. It integrates every out-of-the-money
    option, weighted by 1/K^2, which puts most weight on the low strikes -- and
    the skew makes those the highest-volatility ones. So it sits systematically
    above the at-the-money figure.
    """
    g = surface[surface["expiry"] == expiry].sort_values("strike")
    K = g["strike"].to_numpy()
    Q = g["mid"].to_numpy()
    T = float(g["T"].iloc[0])
    F = float(g["F"].iloc[0])

    dK = np.gradient(K)
    K0 = K[K <= F].max()

    variance = ((2 / T) * np.sum(dK / K**2 * np.exp(r * T) * Q)
                - (1 / T) * (F / K0 - 1) ** 2)
    return float(np.sqrt(variance))


if __name__ == "__main__":
    import yfinance as yf

    surface = pd.read_csv(SURFACE).dropna(subset=["iv"])
    measured = atm_curve(surface)
    gridded = interpolate_tenors(measured)

    print("--- measured, at whatever expiries exist ---")
    print(measured.assign(atm_iv=lambda d: (100 * d.atm_iv).round(2))
                  [["expiry", "days", "atm_iv"]].to_string(index=False))

    print()
    print("--- interpolated onto standard tenors ---")
    print(gridded.assign(atm_iv=lambda d: (100 * d.atm_iv).round(2))
                 [["days", "atm_iv"]].to_string(index=False))

    near30 = measured.iloc[(measured["days"] - 30).abs().argmin()]
    vix = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1]) / 100
    ours_atm = float(gridded.loc[gridded["days"] == 30, "atm_iv"].iloc[0])
    ours_vix = vix_style_vol(surface, near30["expiry"])

    print()
    print("--- validation against VIX ---")
    print(f"our at-the-money, 30d       {100 * ours_atm:.2f}%")
    print(f"our VIX-style calculation   {100 * ours_vix:.2f}%")
    print(f"published VIX               {100 * vix:.2f}%")
