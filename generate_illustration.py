#!/usr/bin/env python3
"""Generate math exercise illustrations via Demeterics API (gpt-image-1.5).

Usage:
    # Generate a single illustration
    python3 generate_illustration.py --prompt "A number line from -8 to 8 ..." --output exercises/images/numberline1.png

    # Process a markdown file — find <!-- ILLUSTRATION: ... --> tags and generate images
    python3 generate_illustration.py --process exercises/practice-YYYY-MM-DD.md

The --process mode scans for HTML comment tags and replaces them with markdown image
references. Three tag flavors are supported:

    <!-- ILLUSTRATION_SECTION: ... -->   → 1024x1024 (1:1 square), filename `section_<hash>.png`
                                            Large scene-setter for each section header.
    <!-- ILLUSTRATION_EXERCISE: ... -->  → 1280x768 (5:3 wide), filename `exercise_<hash>.png`
                                            Smaller companion image for individual exercises.
    <!-- ILLUSTRATION: ... -->           → backward-compat; behaves like SECTION.

Note: gemini-3.1-flash-image-preview accepts only a narrow set of sizes.
As of 2026-04, verified working: 1024x1024 and 1280x768. Other sizes
(1536x1024, 1280x720, 1920x1080, 1024x1536, 1152x896, 1344x768, 1408x768)
return HTTP 400 "unsupported size". See test_illustration_sizes.py.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error

API_URL = "https://api.demeterics.com/imagen/v1/generate"

# Ligne Claire (Hergé / Tintin / Spirou et Fantasio) style — for hero images.
# Clean uniform line weights, flat color fills, no shading gradients, single figure focus.
HERO_STYLE_PREAMBLE = (
    "/// APP SchoolMathPractice\n"
    "/// FLOW hero.illustration\n"
    "/// STYLE ligne_claire\n"
    "\n"
    "Draw in the LIGNE CLAIRE style of Hergé (Tintin) and Franquin (Spirou et Fantasio): "
    "clean uniform black outlines of consistent weight, flat areas of solid color with NO "
    "shading, NO gradients, NO cross-hatching, NO painterly brushwork, NO photorealism. "
    "Simple geometric shapes, warm friendly expressions, clear silhouettes. "
    "European comic-album aesthetic circa 1960s-70s — like a single panel from a Tintin "
    "album redrawn for this scene. White or very light flat background, just enough "
    "setting detail to place the character in the scene.\n\n"
    "CHARACTER FIDELITY: Exactly ONE figure in the frame — a single person, no duplicates, "
    "no mirrored copies, no second character lurking in the background. Full-body or "
    "three-quarter pose. Warm, expressive face.\n\n"
    "FORBIDDEN: No text, no captions, no speech bubbles, no math symbols, no equations, "
    "no Greek letters, no trigonometry, no coordinate grids, no measurement labels. "
    "The image is purely a SCENE, nothing else.\n"
)

# Shared preamble injected into every prompt to enforce clean diagrammatic style
STYLE_PREAMBLE = (
    "/// APP SchoolMathPractice\n"
    "/// FLOW exercise.illustration\n"
    "/// PRODUCT WeeklyMathWorksheet\n"
    "/// ENV production\n"
    "\n"
    "Create a SCENE illustration on a clean white or simple background. "
    "This is a storybook-style scenic illustration for a middle-school worksheet — "
    "depict the situation described, not math.\n\n"
    "ABSOLUTE RULES — the image must NOT contain ANY of the following:\n"
    "  • No mathematical formulas or equations of any kind\n"
    "  • No variables, no letters like x, y, n, r, a, b, c used as math symbols\n"
    "  • No trigonometry labels (tan, sin, cos, θ, angle labels, slope labels)\n"
    "  • No Greek letters (α, β, θ, π, etc.)\n"
    "  • No coordinate axes, grid lines, or plot lines unless the prompt explicitly asks\n"
    "  • No algebra, no inequality symbols, no function notation, no sigma/summation\n"
    "  • No '=', '≥', '≤', '>', '<' symbols floating in the scene\n"
    "  • No measurement callouts like 'd = 500m', 'h = 150m', 'Slope = ...'\n"
    "  • No arrows labeled with math expressions\n\n"
    "If the scene naturally includes numbers (e.g., a scoreboard showing '14' or a sign "
    "saying 'Fort capacity: 400'), those are fine as PLAIN INTEGERS only. Never as "
    "formulas. The audience is a 6th- or 8th-grader studying basic arithmetic, pre-algebra, "
    "or Integrated Math 1 — do NOT draw anything from trigonometry, calculus, or geometry "
    "beyond basic shapes.\n\n"
    "Style: clean illustrated look with sharp lines and readable shapes, muted realistic "
    "colors, no 3D effects, no gradient-heavy rendering. Think educational storybook, "
    "not technical diagram. The image supports the narrative; the math lives elsewhere.\n"
)


def generate_image(prompt: str, api_key: str, output_path: str,
                   size: str = "1024x1024", quality: str = "low",
                   style: str = "scene") -> str:
    """Generate an illustration and save to output_path. Returns the path.

    style: "scene" (default scenic preamble) or "hero" (Ligne Claire hero preamble).
    """
    preamble = HERO_STYLE_PREAMBLE if style == "hero" else STYLE_PREAMBLE
    full_prompt = preamble + prompt

    payload = json.dumps({
        "provider": "google",
        "model": "gemini-3.1-flash-image-preview",
        "prompt": full_prompt,
        "size": size,
        "n": 1,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Demeterics API returned {e.code}: {body}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"ERROR: Demeterics API request failed: {e}", file=sys.stderr)
        return ""

    images = data.get("images", [])
    if not images:
        print(f"ERROR: No images in response: {data}", file=sys.stderr)
        return ""

    image_url = images[0]["url"]
    cost = data.get("cost_usd", "?")
    print(f"  Generated image (${cost}) — downloading...", file=sys.stderr)

    # Download the image
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    try:
        urllib.request.urlretrieve(image_url, output_path)
    except Exception as e:
        print(f"ERROR: Failed to download image: {e}", file=sys.stderr)
        return ""

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Saved: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
    return output_path


def process_markdown(md_path: str, api_key: str, images_dir: str | None = None) -> int:
    """Scan markdown for ILLUSTRATION_SECTION / ILLUSTRATION_EXERCISE / ILLUSTRATION tags,
    generate images at the right aspect ratio, and replace tags with markdown image refs.

    - ILLUSTRATION_SECTION → 1024x1024, filename prefix `section_`
    - ILLUSTRATION_EXERCISE → 1280x768, filename prefix `exercise_`
    - ILLUSTRATION → legacy; treated as SECTION (1024x1024, `section_`)

    The filename prefix is how md_to_pdf.py picks the CSS class at PDF render time.
    Returns the number of illustrations generated (cache hits count as generated).
    """
    with open(md_path, "r") as f:
        content = f.read()

    if images_dir is None:
        images_dir = os.path.join(os.path.dirname(md_path), "images")

    # Tag flavors: name → (filename_prefix, image_size)
    flavors = {
        "ILLUSTRATION_SECTION":  ("section",  "1024x1024"),
        "ILLUSTRATION_EXERCISE": ("exercise", "1280x768"),
        "ILLUSTRATION":          ("section",  "1024x1024"),  # backward-compat
    }

    # Match any of the three tags. Use a single pass so we replace in source order
    # (reversed, so offsets stay valid).
    pattern = r"<!-- (ILLUSTRATION_SECTION|ILLUSTRATION_EXERCISE|ILLUSTRATION): (.+?) -->"
    matches = list(re.finditer(pattern, content))

    if not matches:
        print(f"No ILLUSTRATION tags found in {md_path}", file=sys.stderr)
        return 0

    print(f"Found {len(matches)} illustration tag(s) in {md_path}", file=sys.stderr)
    count = 0

    for match in reversed(matches):
        tag_name = match.group(1)
        prompt = match.group(2).strip()
        prefix, size = flavors[tag_name]

        # Deterministic filename from (prefix + prompt) so different sizes of the same
        # prompt don't collide.
        prompt_hash = hashlib.sha256(f"{prefix}:{prompt}".encode()).hexdigest()[:12]
        filename = f"{prefix}_{prompt_hash}.png"
        filepath = os.path.join(images_dir, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"  Cached: {filename}", file=sys.stderr)
        else:
            print(f"  Generating {tag_name} ({size}): {prompt[:80]}...", file=sys.stderr)
            result = generate_image(prompt, api_key, filepath, size=size)
            if not result:
                print(f"  SKIPPED (generation failed)", file=sys.stderr)
                continue

        alt = prompt[:100].replace('"', "'")
        rel_path = os.path.relpath(filepath, os.path.dirname(md_path))
        replacement = f"![{alt}]({rel_path})"

        content = content[:match.start()] + replacement + content[match.end():]
        count += 1

    with open(md_path, "w") as f:
        f.write(content)

    print(f"Replaced {count}/{len(matches)} illustration tags in {md_path}", file=sys.stderr)
    return count


def main():
    parser = argparse.ArgumentParser(description="Generate math exercise illustrations")
    parser.add_argument("--prompt", help="Image prompt (single image mode)")
    parser.add_argument("--output", help="Output path (single image mode)")
    parser.add_argument("--process", help="Markdown file to scan for ILLUSTRATION tags")
    parser.add_argument("--images-dir", help="Directory for generated images (default: exercises/images/)")
    parser.add_argument("--size", default="1024x1024", help="Image size (default: 1024x1024). Supported: 1024x1024, 1280x768")
    parser.add_argument("--quality", default="low", help="Quality: low, medium, high (default: low)")
    parser.add_argument("--style", default="scene", choices=["scene", "hero"],
                        help="Style preamble: 'scene' (default) or 'hero' (Ligne Claire)")
    args = parser.parse_args()

    api_key = os.environ.get("DEMETERICS_API_KEY", "")
    if not api_key:
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEMETERICS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not api_key:
        print("ERROR: DEMETERICS_API_KEY not found in env or .env file", file=sys.stderr)
        sys.exit(1)

    if args.process:
        count = process_markdown(args.process, api_key, args.images_dir)
        if count == 0:
            sys.exit(1)
    elif args.prompt:
        output = args.output or "illustration.png"
        result = generate_image(args.prompt, api_key, output, args.size, args.quality, args.style)
        if not result:
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
