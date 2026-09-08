#!/usr/bin/env python3

import io
import json
import urllib.error
import urllib.request

import refinery_runner as current


bot = current.bot


def post_discord_image_with_foxlogi_link(content, image_path):
    """Post the dashboard with a masked Foxlogi hyperlink and no link preview."""
    message = (
        f"{content}\n\n"
        "For more information and the full logistics planner, visit "
        "[Foxlogi](https://foxlogi.com/)."
    )

    boundary = "----NOBLEFoxlogiDashboardBoundary"

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    payload_json = json.dumps(
        {
            "content": message,
            "allowed_mentions": {"parse": []},
            # Discord MessageFlags.SUPPRESS_EMBEDS
            "flags": 4,
        }
    ).encode("utf-8")

    body = io.BytesIO()

    def line(value=b""):
        body.write(value)
        body.write(b"\r\n")

    boundary_bytes = boundary.encode("utf-8")

    line(b"--" + boundary_bytes)
    line(b'Content-Disposition: form-data; name="payload_json"')
    line(b"Content-Type: application/json")
    line()
    line(payload_json)

    line(b"--" + boundary_bytes)
    line(
        b'Content-Disposition: form-data; '
        b'name="files[0]"; filename="noble_foxlogi_dashboard.png"'
    )
    line(b"Content-Type: image/png")
    line()
    body.write(image_bytes)
    line()

    line(b"--" + boundary_bytes + b"--")

    req = urllib.request.Request(
        bot.DISCORD_WEBHOOK_URL,
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": bot.USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status not in (200, 204):
                raise RuntimeError(
                    f"Discord returned HTTP {response.status}"
                )

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Discord returned HTTP {exc.code}: {detail}"
        ) from exc


bot.post_discord_image = post_discord_image_with_foxlogi_link


if __name__ == "__main__":
    bot.main()
