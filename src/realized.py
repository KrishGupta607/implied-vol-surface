"""Compare implied volatility against volatility SPY actually realized.

Implied volatility is what the market charged for future movement. Realized
volatility is how much the underlying actually moved. The gap between them is
the variance risk premium: what buyers of options paid for protection above
what the protection turned out to be worth.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from style import SURFACE_COLOR, INK, INK_SOFT, ACCENT, CONTRAST, style_axes
from term_structure import atm_iv

ROOT = Path(__file__).resolve().parent.parent
SURFACE = ROOT / "data" / "surface.csv"
FIGURES = ROOT / "figures"

TRADING_DAYS = 252


def daily_closes(ticker="SPY", period="3y"):
    """SPY's daily closing prices."""
    return yf.Ticker(ticker).history(period=period)["Close"]


def realized_vol(closes, window):
    """Annualized close-to-close realized volatility over the last `window` days.

    Daily log returns only exist on trading days, so the annualization factor is
    sqrt(252), not sqrt(365). Time to expiry stays on a calendar basis because a
    contract expires on a date -- both end up expressed per calendar year, so
    they are directly comparable.
    """
    log_returns = np.log(closes / closes.shift(1)).dropna()
    return float(log_returns.tail(window).std(ddof=1) * np.sqrt(TRADING_DAYS))


def compare(surface, closes):
    """One row per expiry: implied vs realized over a matched lookback."""
    rows = []
    for expiry, group in surface.groupby("expiry"):
        calendar_days = round(group["T"].iloc[0] * 365)
        window = max(5, round(group["T"].iloc[0] * TRADING_DAYS))
        rows.append({
            "expiry": expiry,
            "days": calendar_days,
            "implied": atm_iv(group),
            "realized": realized_vol(closes, window),
        })

    out = pd.DataFrame(rows).sort_values("days").reset_index(drop=True)
    out["premium"] = out["implied"] - out["realized"]
    return out


def plot_comparison(table, path):
    """Implied against realized volatility, by horizon."""
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE_COLOR)
    style_axes(ax)

    days = table["days"]
    implied = table["implied"] * 100
    realized = table["realized"] * 100

    ax.fill_between(days, realized, implied, color=ACCENT, alpha=0.10,
                    linewidth=0, zorder=2)
    ax.plot(days, implied, color=ACCENT, linewidth=1.8, zorder=3, label="implied")
    ax.plot(days, implied, "o", color=ACCENT, markersize=6,
            markeredgecolor=SURFACE_COLOR, markeredgewidth=1.5, zorder=4)
    ax.plot(days, realized, color=CONTRAST, linewidth=1.8, zorder=3, label="realized")
    ax.plot(days, realized, "o", color=CONTRAST, markersize=6,
            markeredgecolor=SURFACE_COLOR, markeredgewidth=1.5, zorder=4)

    ax.annotate("implied", xy=(days.iloc[-1], implied.iloc[-1]), xytext=(-6, 11),
                textcoords="offset points", ha="right", color=ACCENT,
                fontsize=10, fontweight="bold")
    ax.annotate("realized", xy=(days.iloc[-1], realized.iloc[-1]), xytext=(-6, -18),
                textcoords="offset points", ha="right", color=CONTRAST,
                fontsize=10, fontweight="bold")

    ax.set_xlabel("horizon  (days)", color=INK_SOFT, fontsize=10, labelpad=8)
    ax.set_ylabel("annualized volatility  (%)", color=INK_SOFT, fontsize=10, labelpad=8)
    ax.set_title("Implied versus realized volatility", color=INK, fontsize=14,
                 fontweight="bold", loc="left", pad=34)
    ax.text(0, 1.025, "The shaded gap is what option buyers paid above what SPY actually moved",
            transform=ax.transAxes, color=INK_SOFT, fontsize=10)
    ax.legend(frameon=False, fontsize=9, loc="lower right",
              labelcolor=INK_SOFT)

    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE_COLOR)
    plt.close(fig)


if __name__ == "__main__":
    surface = pd.read_csv(SURFACE).dropna(subset=["iv"])
    closes = daily_closes()
    table = compare(surface, closes)

    print(table.assign(
        implied=lambda d: (100 * d.implied).round(2),
        realized=lambda d: (100 * d.realized).round(2),
        premium=lambda d: (100 * d.premium).round(2),
    ).to_string(index=False))
    print(f"\nmean variance risk premium: {100 * table['premium'].mean():+.2f} vol points")

    FIGURES.mkdir(exist_ok=True)
    plot_comparison(table, FIGURES / "implied_vs_realized.png")
    print(f"wrote {FIGURES / 'implied_vs_realized.png'}")
