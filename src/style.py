"""Shared chart styling, so every figure in the project reads as one set."""

SURFACE_COLOR = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e3e2df"

ACCENT = "#2a78d6"       # primary series
CONTRAST = "#eb6834"     # second series, when a chart has two

# Blue sequential ramp, light to dark. Expiry is an ordered quantity, not a set
# of unrelated categories, so colour encodes maturity rather than identity.
RAMP = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
        "#256abf", "#1c5cab", "#184f95", "#104281"]


def style_axes(ax):
    """Recessive grid and axes, so the data carries the chart."""
    ax.set_facecolor(SURFACE_COLOR)
    ax.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=9, length=0)
