"""Figures for the report. Numbers are copied from the live evaluation run
(server._EVALUATION on the 152-message benchmark, seed-2026 shift with cached
Claude Sonnet 5.5 verdicts)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

OUT = os.path.dirname(os.path.abspath(__file__))
for f in ("Arial.ttf", "Arial Bold.ttf"):
    font_manager.fontManager.addfont(f"/System/Library/Fonts/Supplemental/{f}")
plt.rcParams.update({"font.family": "Arial", "font.size": 9})

INK, SOFT, MUTED, GRID = "#1f1f1e", "#55544f", "#8a897f", "#e6e5df"
BLUE, ORANGE = "#2a78d6", "#eb6834"   # validated categorical slots 1 and 2


def recall_chart():
    labels = ["Baseline model alone",
              "Safety rules alone",
              "Full pipeline, LLM outage",
              "Full pipeline, LLM online*"]
    urgent = [85, 65, 98, 100]
    critical = [52, 70, 100, 100]

    fig, ax = plt.subplots(figsize=(6.6, 2.6), dpi=300)
    h = 0.34
    ys = list(range(len(labels)))[::-1]
    for y, u, c in zip(ys, urgent, critical):
        ax.barh(y + h / 2 + 0.02, u, height=h, color=BLUE)
        ax.barh(y - h / 2 - 0.02, c, height=h, color=ORANGE)
        ax.text(u + 1, y + h / 2 + 0.02, f"{u}%", va="center", fontsize=8, color=INK)
        ax.text(c + 1, y - h / 2 - 0.02, f"{c}%", va="center", fontsize=8, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, color=INK)
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color=SOFT)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", length=0)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
              labels=["Urgent recall (high + critical reach the fast lane)", "Critical recall (marked critical)"],
              loc="lower center", bbox_to_anchor=(0.42, 1.0), ncol=2, frameon=False, fontsize=8,
              handlelength=1.2, labelcolor=SOFT)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_recall.png"), bbox_inches="tight")
    plt.close(fig)


def pipeline_diagram():
    fig, ax = plt.subplots(figsize=(7.0, 2.5), dpi=300)
    ax.set_xlim(-1, 101)
    ax.set_ylim(-2, 36)
    ax.axis("off")

    def box(x, y, w, h, title, sub, edge=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.0",
                                    linewidth=0.9, edgecolor=edge, facecolor="#ffffff"))
        ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center", fontsize=7, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=5.8, color=SOFT, linespacing=1.3)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=0.8, shrinkA=0, shrinkB=0))

    box(-0.5, 26, 16.5, 7, "Message", "SMS, email, web form")
    ax.text(31, 34.6, "Priority: each step can only raise it", ha="center", fontsize=6.4, color=SOFT, style="italic")
    rows = [("1  Claude LLM", "or baseline if LLM is down"),
            ("2  Safety rules", "danger phrases set a minimum"),
            ("3  Readability check", "unreadable text: at least high"),
            ("4  Access weighting", "cut off by flood: bumped up")]
    for i, (t, sub) in enumerate(rows):
        box(19, 26 - i * 8.6, 24, 7, t, sub, edge=BLUE)
        if i:
            arrow(31, 26 - (i - 1) * 8.6 - 0.3, 31, 26 - i * 8.6 + 7.3)
    arrow(16.3, 29.5, 18.6, 29.5)

    box(47, 13, 17, 7, "Route + explain", "team, reason, draft")
    arrow(43.5, 3.5, 47.2, 13.5)

    box(68, 26, 32, 7, "Officer reads and acknowledges", "approves the draft reply (never auto-sent)", edge=ORANGE)
    box(68, 12.5, 32, 9, "Not picked up in time?", "critical: 15 min, then shift supervisor\nstill waiting at 2x the limit: duty manager", edge=ORANGE)
    box(68, 1, 32, 7.5, "Sender went silent?", "flagged for a welfare check")
    arrow(63.8, 18.5, 67.6, 28.5)
    arrow(63.8, 16.5, 67.6, 17)
    arrow(63.8, 14.5, 67.6, 5)
    fig.savefig(os.path.join(OUT, "fig_pipeline.png"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    recall_chart()
    pipeline_diagram()
    print("ok")
