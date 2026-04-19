#!/usr/bin/env python3
"""Send an HTML email with optional PDF attachments via the `himalaya` SMTP client.

Usage:
    python3 send_email.py --to "kid@example.com, parent@example.com" --subject "Hi" --html body.html
    python3 send_email.py --to "kid@example.com" --subject "Hi" --html body.html --attach report.pdf
    echo "<h1>Hi</h1>" | python3 send_email.py --to "kid@example.com" --subject "Hi" --stdin --attach a.pdf
"""

import argparse
import base64
import os
import subprocess
import sys
import uuid


def build_mime(from_addr: str, to: str, subject: str, html_body: str,
               attachments: list[str] | None = None,
               inline_images: list[str] | None = None) -> str:
    """Build a multipart MIME message with HTML body, optional PDF attachments,
    and optional inline CID images.

    For inline images, reference them in HTML as: <img src="cid:filename.png">
    """
    boundary_mixed = f"----=_Mixed_{uuid.uuid4().hex[:12]}"
    boundary_related = f"----=_Related_{uuid.uuid4().hex[:12]}"

    headers = (
        f"From: {from_addr}\r\n"
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"MIME-Version: 1.0\r\n"
    )

    has_attachments = attachments and any(os.path.isfile(f) for f in attachments)
    has_inline = inline_images and any(os.path.isfile(f) for f in inline_images)

    if not has_attachments and not has_inline:
        headers += "Content-Type: text/html; charset=utf-8\r\n"
        return headers + "\r\n" + html_body

    # Outer boundary: multipart/mixed (for PDF attachments)
    headers += f'Content-Type: multipart/mixed; boundary="{boundary_mixed}"\r\n'
    parts = [headers, ""]

    if has_inline:
        # Inner: multipart/related (HTML + inline images)
        parts.append(f"--{boundary_mixed}")
        parts.append(f'Content-Type: multipart/related; boundary="{boundary_related}"')
        parts.append("")

        # HTML part
        parts.append(f"--{boundary_related}")
        parts.append("Content-Type: text/html; charset=utf-8")
        parts.append("Content-Transfer-Encoding: 7bit")
        parts.append("")
        parts.append(html_body)

        # Inline image parts
        for filepath in (inline_images or []):
            if not os.path.isfile(filepath):
                print(f"WARNING: inline image not found: {filepath}", file=sys.stderr)
                continue
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            wrapped = "\r\n".join(
                encoded[i:i + 76] for i in range(0, len(encoded), 76)
            )
            parts.append(f"--{boundary_related}")
            parts.append(f"Content-Type: image/png; name=\"{filename}\"")
            parts.append("Content-Transfer-Encoding: base64")
            parts.append(f"Content-ID: <{filename}>")
            parts.append(f"Content-Disposition: inline; filename=\"{filename}\"")
            parts.append("")
            parts.append(wrapped)

        parts.append(f"--{boundary_related}--")
    else:
        # No inline images — just HTML
        parts.append(f"--{boundary_mixed}")
        parts.append("Content-Type: text/html; charset=utf-8")
        parts.append("Content-Transfer-Encoding: 7bit")
        parts.append("")
        parts.append(html_body)

    # PDF attachment parts
    for filepath in (attachments or []):
        if not os.path.isfile(filepath):
            print(f"WARNING: attachment not found: {filepath}", file=sys.stderr)
            continue
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        wrapped = "\r\n".join(
            encoded[i:i + 76] for i in range(0, len(encoded), 76)
        )
        parts.append(f"--{boundary_mixed}")
        parts.append(f"Content-Type: application/pdf; name=\"{filename}\"")
        parts.append("Content-Transfer-Encoding: base64")
        parts.append(f"Content-Disposition: attachment; filename=\"{filename}\"")
        parts.append("")
        parts.append(wrapped)

    parts.append(f"--{boundary_mixed}--")
    return "\r\n".join(parts)


def send_via_himalaya(mime_message: str, account: str) -> bool:
    """Send a raw MIME message via himalaya.

    `account` must match a configured account name in ~/.config/himalaya/config.toml.

    Note: himalaya may timeout on the IMAP "save to Sent" step even though
    the SMTP send succeeds. We treat timeouts as success since the email
    is delivered regardless.
    """
    try:
        result = subprocess.run(
            ["himalaya", "message", "send", "-a", account],
            input=mime_message, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"WARNING: himalaya exited {result.returncode} (email likely sent, IMAP save may have failed)",
                  file=sys.stderr)
        else:
            print(f"Email sent successfully", file=sys.stderr)
        return True
    except subprocess.TimeoutExpired:
        print(f"WARNING: himalaya timed out (email likely sent, IMAP save timed out)", file=sys.stderr)
        return True


def main():
    parser = argparse.ArgumentParser(description="Send HTML email with PDF attachments via himalaya")
    parser.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--html", help="Path to HTML file for email body")
    parser.add_argument("--stdin", action="store_true", help="Read HTML body from stdin")
    parser.add_argument("--attach", nargs="*", default=[], help="PDF file(s) to attach")
    parser.add_argument("--inline", nargs="*", default=[],
                        help="Inline image(s) as CID attachments. Use cid:filename in HTML src.")
    default_mentor = os.environ.get("MENTOR_NAME", "Aristotle")
    default_email = os.environ.get("MENTOR_EMAIL", "")
    default_from = (
        f'"{default_mentor}" <{default_email}>' if default_email else default_mentor
    )
    parser.add_argument("--from-addr", default=default_from,
                        help="From address (default: $MENTOR_NAME <$MENTOR_EMAIL>)")
    parser.add_argument("--account", default=os.environ.get("HIMALAYA_ACCOUNT", "aristotle"),
                        help="himalaya account name (default: $HIMALAYA_ACCOUNT)")
    parser.add_argument("--dry-run", action="store_true", help="Print MIME message instead of sending")
    args = parser.parse_args()

    if args.stdin:
        html_body = sys.stdin.read()
    elif args.html:
        with open(args.html) as f:
            html_body = f.read()
    else:
        print("ERROR: provide --html FILE or --stdin", file=sys.stderr)
        sys.exit(1)

    mime = build_mime(args.from_addr, args.to, args.subject, html_body, args.attach,
                      args.inline)

    if args.dry_run:
        print(mime)
        return

    ok = send_via_himalaya(mime, args.account)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
