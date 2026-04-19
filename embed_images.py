#!/usr/bin/env python3
"""Embed local images in HTML as base64 data URIs.

Usage:
    python3 embed_images.py input.html [output.html]
    python3 embed_images.py input.html --base-dir exercises/

Finds all <img src="path/to/image.png"> tags and replaces the src with
base64 data URIs so images display inline in emails without external hosting.
If output is omitted, overwrites the input file.
"""

import base64
import mimetypes
import os
import re
import sys


def embed_images(html_path, output_path=None, base_dir=None):
    """Replace local image src paths with base64 data URIs."""
    if output_path is None:
        output_path = html_path

    with open(html_path, "r") as f:
        html = f.read()

    if base_dir is None:
        base_dir = os.path.dirname(html_path) or "."

    count = 0

    def replace_src(match):
        nonlocal count
        src = match.group(1)

        # Skip if already a data URI or external URL
        if src.startswith(("data:", "http://", "https://")):
            return match.group(0)

        # Resolve path
        img_path = src
        if not os.path.isabs(img_path):
            img_path = os.path.join(base_dir, img_path)

        if not os.path.isfile(img_path):
            print(f"  WARNING: image not found: {img_path}", file=sys.stderr)
            return match.group(0)

        # Read and encode
        mime_type = mimetypes.guess_type(img_path)[0] or "image/png"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        count += 1
        size_kb = os.path.getsize(img_path) / 1024
        print(f"  Embedded: {os.path.basename(img_path)} ({size_kb:.0f} KB)", file=sys.stderr)
        return f'src="data:{mime_type};base64,{b64}"'

    html = re.sub(r'src="([^"]+)"', replace_src, html)

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Embedded {count} images in {output_path}", file=sys.stderr)
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.html [output.html] [--base-dir DIR]", file=sys.stderr)
        sys.exit(1)

    html_file = sys.argv[1]
    output_file = None
    base_dir = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--base-dir" and i + 1 < len(sys.argv):
            base_dir = sys.argv[i + 1]
            i += 2
        else:
            output_file = sys.argv[i]
            i += 1

    embed_images(html_file, output_file, base_dir)
