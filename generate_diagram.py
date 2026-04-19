#!/usr/bin/env python3
"""Generate precise math diagrams using matplotlib.

Usage:
    # Number line
    python3 generate_diagram.py numberline --range -8,8 --dots "-7,-4,-1,0,2,5" --output out.png

    # Number line with inequality
    python3 generate_diagram.py inequality --point 8 --direction left --circle open --range 0,12 --output out.png

    # Process markdown — find <!-- DIAGRAM: ... --> tags and generate images
    python3 generate_diagram.py --process exercises/practice-YYYY-MM-DD.md

The --process mode scans for tags like:
    <!-- DIAGRAM: numberline | range=-8,8 | dots=-7,-4,-1,0,2,5 | labels=true -->
    <!-- DIAGRAM: inequality | point=8 | direction=left | circle=open | range=0,12 -->
    <!-- DIAGRAM: numberline | range=-10,10 | dots=-7,5 | arc=-7,5,distance=12 -->
"""

import argparse
import hashlib
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


BLUE = "#2563eb"
RED = "#dc2626"
GREEN = "#059669"
GRAY = "#6b7280"


def _nice_step(span, target_ticks=12):
    """Return a 'nice' tick step so the axis has ~target_ticks labels."""
    raw = max(1, span / target_ticks)
    # Round up to nearest {1,2,5} * 10^k
    import math
    exp = int(math.floor(math.log10(raw)))
    base = 10 ** exp
    for m in (1, 2, 5, 10):
        if m * base >= raw:
            return int(m * base)
    return int(10 * base)


def draw_numberline(ax, lo, hi, dots=None, dot_labels=True, arc=None, bracket=None, title=None):
    """Draw a precise number line with optional dots, arc, and bracket."""
    span = hi - lo
    margin = max(0.8, span * 0.04)
    ax.set_xlim(lo - margin, hi + margin)
    ax.set_ylim(-1.5, 2.0)
    # Only force equal aspect for narrow ranges — wider ranges need auto aspect
    # to avoid matplotlib squishing labels horizontally.
    if span <= 20:
        ax.set_aspect("equal")
    ax.axis("off")

    # Main line with arrows
    arrow_pad = max(0.5, span * 0.02)
    ax.annotate("", xy=(hi + arrow_pad, 0), xytext=(lo - arrow_pad, 0),
                arrowprops=dict(arrowstyle="<->", lw=1.5, color="black"))

    # Tick marks at every integer (small, unlabeled for wide ranges);
    # labels only at a nice step so they don't overlap.
    step = _nice_step(span)
    label_start = -((-lo) // step) * step  # smallest multiple of step >= lo
    tick_len = 0.15 if span <= 20 else 0.22
    for i in range(lo, hi + 1):
        if span <= 20:
            ax.plot([i, i], [-tick_len, tick_len], color="black", lw=1.2)
    # Labeled major ticks
    major = []
    v = label_start
    while v <= hi:
        if v >= lo:
            major.append(v)
        v += step
    # Ensure endpoints are labeled for context on wide ranges
    if span > 20:
        if lo not in major:
            major.insert(0, lo)
        if hi not in major:
            major.append(hi)
    for i in major:
        ax.plot([i, i], [-tick_len, tick_len], color="black", lw=1.4)
        ax.text(i, -tick_len - 0.15, str(i), ha="center", va="top",
                fontsize=9, fontfamily="sans-serif")

    # Dashed origin line
    if lo <= 0 <= hi:
        ax.plot([0, 0], [-0.15, 0.6], color=GRAY, lw=0.8, ls="--")

    # Plot dots
    if dots:
        for val in dots:
            ax.plot(val, 0, "o", color=BLUE, markersize=10, zorder=5)
            if dot_labels:
                ax.text(val, 0.5, str(val), ha="center", va="bottom", fontsize=10,
                        fontweight="bold", color=BLUE, fontfamily="sans-serif")

    # Arc annotation (e.g., distance between two points)
    if arc:
        x1, x2, label = arc
        mid = (x1 + x2) / 2
        span = abs(x2 - x1)
        arc_height = min(1.5, 0.3 + span * 0.08)
        style = f"arc3,rad=-{0.2 + span * 0.01:.2f}"
        ax.annotate("", xy=(x2, 0.3), xytext=(x1, 0.3),
                    arrowprops=dict(arrowstyle="->", lw=1.5, color=RED,
                                    connectionstyle=style))
        ax.text(mid, arc_height + 0.3, label, ha="center", va="bottom",
                fontsize=10, color=RED, fontfamily="sans-serif")

    # Bracket below (e.g., "least to greatest →")
    if bracket:
        x1, x2, label = bracket
        y = -1.0
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", lw=1.5, color=GREEN))
        ax.plot([x1, x1], [y - 0.05, y + 0.2], color=GREEN, lw=1.5)
        ax.text((x1 + x2) / 2, y - 0.25, label, ha="center", va="top",
                fontsize=10, color=GREEN, fontfamily="sans-serif")

    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=15)


def draw_inequality(ax, lo, hi, point, direction, circle_type, label=None):
    """Draw an inequality on a number line (open/closed circle + arrow)."""
    draw_numberline(ax, lo, hi)

    # Circle
    if circle_type == "open":
        ax.plot(point, 0, "o", color=BLUE, markersize=12, markerfacecolor="white",
                markeredgewidth=2, zorder=5)
    else:  # closed
        ax.plot(point, 0, "o", color=BLUE, markersize=12, zorder=5)

    # Arrow/shading
    if direction == "left":
        ax.annotate("", xy=(lo - 0.3, 0), xytext=(point, 0),
                    arrowprops=dict(arrowstyle="-|>", lw=3, color=BLUE))
    else:
        ax.annotate("", xy=(hi + 0.3, 0), xytext=(point, 0),
                    arrowprops=dict(arrowstyle="-|>", lw=3, color=BLUE))

    if label:
        ax.text(point, 0.7, label, ha="center", va="bottom", fontsize=11,
                fontweight="bold", color=BLUE, fontfamily="sans-serif")


def render(fig, output_path):
    """Save figure to PNG."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", pad_inches=0.2,
                facecolor="white", edgecolor="none")
    plt.close(fig)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Saved diagram: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)


def generate_from_spec(spec_str, output_path):
    """Parse a DIAGRAM spec string and generate the image.

    Format: "type | key=val | key=val | ..."
    """
    parts = [p.strip() for p in spec_str.split("|")]
    diagram_type = parts[0].lower()
    params = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()

    if diagram_type == "numberline":
        lo, hi = [int(x) for x in params.get("range", "-10,10").split(",")]
        fig, ax = plt.subplots(1, 1, figsize=(12 if (hi - lo) > 40 else 10, 2.5))
        dots = [int(x) for x in params["dots"].split(",")] if "dots" in params else None
        dot_labels = params.get("labels", "true").lower() != "false"
        arc = None
        if "arc" in params:
            arc_parts = params["arc"].split(",")
            arc = (int(arc_parts[0]), int(arc_parts[1]), arc_parts[2] if len(arc_parts) > 2 else "")
        bracket = None
        if "bracket" in params:
            br_parts = params["bracket"].split(",", 2)
            bracket = (int(br_parts[0]), int(br_parts[1]), br_parts[2] if len(br_parts) > 2 else "")
        title = params.get("title")
        draw_numberline(ax, lo, hi, dots, dot_labels, arc, bracket, title)

    elif diagram_type == "inequality":
        lo, hi = [int(x) for x in params.get("range", "0,12").split(",")]
        fig, ax = plt.subplots(1, 1, figsize=(10, 2.5))
        point = float(params.get("point", "0"))
        direction = params.get("direction", "right")
        circle_type = params.get("circle", "open")
        label = params.get("label")
        draw_inequality(ax, lo, hi, point, direction, circle_type, label)

    else:
        print(f"  Unknown diagram type: {diagram_type}", file=sys.stderr)
        return ""

    render(fig, output_path)
    return output_path


def process_markdown(md_path, images_dir=None):
    """Scan markdown for <!-- DIAGRAM: ... --> tags, generate images, replace tags."""
    with open(md_path, "r") as f:
        content = f.read()

    if images_dir is None:
        images_dir = os.path.join(os.path.dirname(md_path), "images")

    pattern = r"<!-- DIAGRAM: (.+?) -->"
    matches = list(re.finditer(pattern, content))

    if not matches:
        print(f"No <!-- DIAGRAM: ... --> tags found in {md_path}", file=sys.stderr)
        return 0

    print(f"Found {len(matches)} diagram(s) in {md_path}", file=sys.stderr)
    count = 0

    for match in reversed(matches):
        spec = match.group(1).strip()
        spec_hash = hashlib.sha256(spec.encode()).hexdigest()[:12]
        filename = f"diagram_{spec_hash}.png"
        filepath = os.path.join(images_dir, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"  Cached: {filename}", file=sys.stderr)
        else:
            print(f"  Generating: {spec[:80]}...", file=sys.stderr)
            result = generate_from_spec(spec, filepath)
            if not result:
                continue

        alt = spec[:100].replace('"', "'")
        rel_path = os.path.relpath(filepath, os.path.dirname(md_path))
        replacement = f"![{alt}]({rel_path})"
        content = content[:match.start()] + replacement + content[match.end():]
        count += 1

    with open(md_path, "w") as f:
        f.write(content)

    print(f"Replaced {count}/{len(matches)} diagram tags in {md_path}", file=sys.stderr)
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate precise math diagrams")
    parser.add_argument("--process", help="Markdown file to scan for DIAGRAM tags")
    parser.add_argument("--spec", help="Diagram spec string (e.g., 'numberline | range=-8,8 | dots=-4,-1,0,1,3')")
    parser.add_argument("--output", default="diagram.png", help="Output path")
    args = parser.parse_args()

    if args.process:
        process_markdown(args.process)
    elif args.spec:
        generate_from_spec(args.spec, args.output)
    else:
        parser.print_help()
