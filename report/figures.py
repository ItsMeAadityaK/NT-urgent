"""
figures.py: draws the report's three diagrams and crops the interface screenshots.

    python report/figures.py

Numbers in the results chart come from results_after.json (written by collect_results.py), never typed.
Screenshots in report/shots/ are taken from the running console.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results_after.json")))

for fam in ("Arial", "Liberation Sans", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except Exception:
        continue

INK, ACCENT, TEAL = "#14171D", "#C1440E", "#0E7C7B"
CRIT, HIGH, MED, LOW = "#D7263D", "#E8590C", "#B8860B", "#2F9E5B"
SOFT, RULE = "#5B5F68", "#D9D6CC"


def box(ax, x, y, w, h, text, fc="white", ec=INK, tc=INK, fs=7, bold=False, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=SOFT, lw=1.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=7, lw=lw, color=color,
                                 shrinkA=0, shrinkB=0))


# ------------------------------------------------------------------ Figure: pipeline
def pipeline():
    fig, ax = plt.subplots(figsize=(6.5, 3.55), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 54)
    ax.axis("off")

    for x, s in [(1, "1  Message arrives"), (21, "2  Two readers"), (51, "3  Floors (can only raise)"), (85, "4  Priority")]:
        ax.text(x, 52, s, fontsize=7, color=SOFT, fontweight="bold")

    box(ax, 1, 31, 15, 17, "SMS\nWeb form\nEmail\nPhone notes\nInbound API", fs=6.8)
    box(ax, 21, 38, 25, 10, "Claude API\nreads the meaning", fc=ACCENT, ec=ACCENT, tc="white", fs=7.2, bold=True)
    box(ax, 21, 25, 25, 10, "Backup ML model\nTF-IDF + logistic regression", fc=TEAL, ec=TEAL, tc="white", fs=6.8, bold=True)
    # the three floors share one frame: whatever the readers say, these can only push it up
    ax.add_patch(FancyBboxPatch((50.5, 20.5), 31, 29, boxstyle="round,pad=0.25,rounding_size=1.2", fc="#F6F4EF", ec=RULE, lw=1.0))
    box(ax, 52.5, 40.5, 27, 7, "Safety tripwires\n10 groups, 61 patterns", fs=6.4)
    box(ax, 52.5, 31, 27, 7, "Unreadable text\nraised to at least high", fs=6.4)
    box(ax, 52.5, 21.8, 27, 7, "Second-opinion floor\nbackup says urgent, AI lower: high", fs=6.0)
    box(ax, 86, 38, 13, 10, "Access\nweighting\nlimited +1\ncut-off +2", fs=6.2)
    for i, c in enumerate([CRIT, HIGH, MED, LOW]):
        ax.add_patch(FancyBboxPatch((86.2 + i * 3.2, 30.6), 2.9, 3.2, boxstyle="round,pad=0.1,rounding_size=0.6", fc=c, ec=c))
    ax.text(92.5, 27.4, "final priority", ha="center", fontsize=6.4, fontweight="bold", color=INK)

    arrow(ax, 16.5, 42, 20.7, 43)
    arrow(ax, 16.5, 38, 20.7, 31)
    arrow(ax, 46.4, 43, 50.2, 40)
    arrow(ax, 46.4, 30, 50.2, 31)
    arrow(ax, 82.0, 38, 85.7, 41)
    arrow(ax, 92.5, 37.6, 92.5, 34.4)

    # bottom row, reached by an elbow from the final priority
    ax.text(1, 21.6, "5  What happens next", fontsize=7, color=SOFT, fontweight="bold")
    ax.plot([92.5, 92.5, 14.5], [26.2, 18.6, 18.6], color=SOFT, lw=1.0)
    arrow(ax, 14.5, 18.6, 14.5, 16.4)
    box(ax, 1, 4.5, 27, 11.5, "Route to one of 11 teams\n+ draft reply (never sent)\nCritical copies the Duty Officer", fs=6.5)
    box(ax, 33, 4.5, 21, 11.5, "A named officer\nacknowledges", fc=INK, ec=INK, tc="white", fs=7, bold=True)
    box(ax, 59, 4.5, 40, 11.5, "Nobody acts in time\nShift supervisor at the limit, Duty manager at twice the limit\nSender goes quiet: welfare check",
        fc="#FBEDE6", ec=ACCENT, fs=6.1)
    arrow(ax, 28.4, 10.2, 32.7, 10.2)
    arrow(ax, 54.4, 10.2, 58.7, 10.2, color=ACCENT)
    fig.tight_layout(pad=0.1)
    fig.savefig(os.path.join(HERE, "fig_pipeline.png"), facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ Figure: results
def results():
    b = R["benchmark"]["rows"]
    order = [("baseline", "Backup model\nalone"), ("rules", "Safety rules\nalone"), ("ai", "Claude API\nalone"),
             ("full", "Full system,\nClaude API online"), ("full_outage", "Full system,\nClaude API offline")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9), dpi=300, gridspec_kw={"width_ratios": [2.15, 1]})
    ys = list(range(len(order)))[::-1]
    for y, (k, label) in zip(ys, order):
        u, c = b[k]["urgent_recall"], b[k]["critical_recall"]
        a1.barh(y + 0.19, u * 100, height=0.34, color=ACCENT)
        a1.barh(y - 0.19, c * 100, height=0.34, color=INK)
        a1.text(u * 100 + 1, y + 0.19, f"{u*100:.0f}%", va="center", fontsize=6.5, color=ACCENT)
        a1.text(c * 100 + 1, y - 0.19, f"{c*100:.0f}%", va="center", fontsize=6.5, color=INK)
        fa = b[k]["false_urgent"]
        a2.barh(y, fa, height=0.5, color=MED)
        a2.text(fa + 0.4, y, f"{fa}", va="center", fontsize=6.5, color=INK)
    a1.set_yticks(ys)
    a1.set_yticklabels([l for _, l in order], fontsize=6.5)
    a1.set_xlim(0, 118)
    a1.set_xticks([0, 25, 50, 75, 100])
    a1.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=6.5)
    a1.set_title("Urgent messages caught", fontsize=7.2, loc="left", color=INK, fontweight="bold")
    a1.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=ACCENT), plt.Rectangle((0, 0), 1, 1, color=INK)],
              labels=["All urgent (high + critical, 55)", "Critical only (23)"], fontsize=6.2, loc="upper center",
              bbox_to_anchor=(0.45, -0.13), ncol=2, frameon=False)
    a2.set_yticks(ys)
    a2.set_yticklabels([])
    a2.set_xlim(0, 16)
    a2.set_xticks([0, 5, 10, 15])
    a2.set_xticklabels(["0", "5", "10", "15"], fontsize=6.5)
    a2.set_title("Routine messages escalated\n(of 97)", fontsize=7.2, loc="left", color=INK, fontweight="bold")
    for a in (a1, a2):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.spines["left"].set_color(RULE)
        a.spines["bottom"].set_color(RULE)
        a.tick_params(length=2, colors=SOFT)
        a.grid(axis="x", color="#EEEBE3", lw=0.6)
        a.set_axisbelow(True)
    fig.tight_layout(pad=0.4, w_pad=1.2)
    fig.savefig(os.path.join(HERE, "fig_results.png"), facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ Figure: escalation clocks
def escalation():
    fig, ax = plt.subplots(figsize=(6.5, 1.95), dpi=300)
    lanes = [("Critical", 15, 2 * 60), ("High", 60, 6 * 60), ("Medium", 240, 24 * 60)]
    x_max = 8 * 60
    for i, (name, lim, drop) in enumerate(lanes):
        y = 2 - i
        ax.barh(y, lim, left=0, height=0.46, color=LOW)
        ax.barh(y, min(lim, x_max - lim), left=lim, height=0.46, color=HIGH)
        if 2 * lim < x_max:
            ax.barh(y, x_max - 2 * lim, left=2 * lim, height=0.46, color=CRIT)
        ax.text(-8, y, f"{name}\nlimit {lim} min", ha="right", va="center", fontsize=6.8, fontweight="bold",
                color=INK, linespacing=1.3)
        if drop <= x_max:
            ax.plot([drop], [y + 0.36], marker="v", color=INK, ms=4)
            ax.text(drop, y + 0.5, f"silent {drop // 60} h", ha="center", va="bottom", fontsize=6, color=INK)
        else:
            ax.text(x_max - 6, y, f"sender flagged silent after {drop // 60} h  →", ha="right", va="center",
                    fontsize=6.2, color="white")
    ax.set_xlim(-75, x_max)
    ax.set_ylim(-0.6, 2.9)
    ax.set_yticks([])
    ax.set_xticks(range(0, 481, 60))
    ax.set_xticklabels([f"{m // 60} h" for m in range(0, 481, 60)], fontsize=6.5, color=SOFT)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(length=2)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in (LOW, HIGH, CRIT)],
              labels=["With the officer", "Escalated to shift supervisor", "Escalated to duty manager"],
              fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.55, 1.2), frameon=False)
    ax.set_xlabel("Time since the message arrived", fontsize=6.5, color=SOFT)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(HERE, "fig_escalation.png"), facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ screenshot crops
def crops():
    def crop(src, dst, box_, maxw=1900):
        path = os.path.join(HERE, "shots", src)
        if not os.path.exists(path):
            return
        im = Image.open(path).convert("RGB").crop(box_)
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        im.save(os.path.join(HERE, dst), optimize=True)

    crop("console.png", "fig_console.png", (150, 40, 2730, 1590))
    crop("journey.png", "fig_journey.png", (190, 1700, 2690, 3200))
    crop("map.png", "fig_map.png", (190, 1750, 1860, 3260))
    crop("eval.png", "fig_eval.png", (190, 2950, 2690, 3440))


if __name__ == "__main__":
    pipeline()
    results()
    escalation()
    crops()
    print("figures written")
