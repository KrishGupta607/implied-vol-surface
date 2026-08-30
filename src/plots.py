"""Plot the implied volatility smile and the term structure."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from style import SURFACE_COLOR, INK, INK_SOFT, ACCENT, RAMP, style_axes
from term_structure import atm_iv

ROOT = Path(__file__).resolve().parent.parent
SURFACE = ROOT / "data" / "surface.csv"
FIGURES = ROOT / "figures"

def plot_smile(df, path):
    """Implied volatility against log-moneyness, one curve per expiry."""
    fig, ax = plt.subplots(figsize=(9, 5.6), facecolor=SURFACE_COLOR)
    style_axes(ax)

    expiries = sorted(df["expiry"].unique())
    for i, expiry in enumerate(expiries):
        g = df[df["expiry"] == expiry].sort_values("log_moneyness")
        days = round(g["T"].iloc[0] * 365)
        ax.plot(g["log_moneyness"], g["iv"] * 100,
                color=RAMP[i], linewidth=1.8, zorder=3,
                label=f"{expiry}   {days:>3d}d")

    ax.axvline(0, color=INK_SOFT, linewidth=0.9, linestyle=(0, (4, 3)), zorder=2)
    ax.annotate("at the money", xy=(0, ax.get_ylim()[1]), xytext=(4, -12),
                textcoords="offset points", color=INK_SOFT, fontsize=9)

    ax.set_xlim(-0.25, 0.15)
    ax.set_xlabel("log-moneyness   ln(K / S)", color=INK_SOFT, fontsize=10, labelpad=8)
    ax.set_ylabel("implied volatility  (%)", color=INK_SOFT, fontsize=10, labelpad=8)
    ax.set_title("SPY implied volatility smile", color=INK, fontsize=14,
                 fontweight="bold", loc="left", pad=34)
    ax.text(0, 1.025, "Downside strikes price far higher volatility than upside strikes",
            transform=ax.transAxes, color=INK_SOFT, fontsize=10)

    leg = ax.legend(title="expiry", frameon=False, fontsize=9,
                    title_fontsize=9, loc="upper right", labelspacing=0.5)
    leg.get_title().set_color(INK_SOFT)
    for text in leg.get_texts():
        text.set_color(INK_SOFT)

    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE_COLOR)
    plt.close(fig)


def plot_term_structure(df, path):
    """At-the-money implied volatility against time to expiry."""
    points = []
    for expiry, g in df.groupby("expiry"):
        points.append((round(g["T"].iloc[0] * 365), atm_iv(g)))
    points.sort()
    days = [p[0] for p in points]
    ivs = [p[1] * 100 for p in points]

    fig, ax = plt.subplots(figsize=(9, 5.0), facecolor=SURFACE_COLOR)
    style_axes(ax)

    ax.plot(days, ivs, color=ACCENT, linewidth=1.8, zorder=3)
    ax.plot(days, ivs, "o", color=ACCENT, markersize=6,
            markeredgecolor=SURFACE_COLOR, markeredgewidth=1.5, zorder=4)

    for i in (0, len(days) - 1):
        ax.annotate(f"{ivs[i]:.1f}%", xy=(days[i], ivs[i]), xytext=(0, 11),
                    textcoords="offset points", ha="center",
                    color=INK, fontsize=9, fontweight="bold")

    ax.set_xlabel("days to expiry", color=INK_SOFT, fontsize=10, labelpad=8)
    ax.set_ylabel("at-the-money implied volatility  (%)", color=INK_SOFT,
                  fontsize=10, labelpad=8)
    ax.set_title("SPY volatility term structure", color=INK, fontsize=14,
                 fontweight="bold", loc="left", pad=34)
    ax.text(0, 1.025, "Longer-dated options price more volatility than near-dated ones",
            transform=ax.transAxes, color=INK_SOFT, fontsize=10)

    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE_COLOR)
    plt.close(fig)


if __name__ == "__main__":
    df = pd.read_csv(SURFACE).dropna(subset=["iv"])
    FIGURES.mkdir(exist_ok=True)

    plot_smile(df, FIGURES / "smile.png")
    plot_term_structure(df, FIGURES / "term_structure.png")
    print(f"wrote {FIGURES / 'smile.png'}")
    print(f"wrote {FIGURES / 'term_structure.png'}")
