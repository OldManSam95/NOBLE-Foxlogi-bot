#!/usr/bin/env python3

import io
import json
import math
import os
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont


FOXLOGI_URL = "https://foxlogi.com/api/logistic/planner/"
FOXLOGI_API_KEY = os.environ["FOXLOGI_API_KEY"].strip()
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"].strip()

USER_AGENT = "NOBLE-Foxlogi-Bot-Test/1.0"
OUTPUT_IMAGE = "noble_foxlogi_dashboard.png"

LONDON = ZoneInfo("Europe/London")


# ============================================================
# DASHBOARD DESIGN
# ============================================================

CANVAS_WIDTH = 1600
MARGIN = 28
PANEL_GAP = 20

BACKGROUND = "#0F172A"
PANEL_BG = "#111827"
CARD_BG = "#1F2937"
INNER_BG = "#182232"

TEXT = "#F1F5F9"
MUTED = "#94A3B8"
ACCENT = "#38BDF8"
CATEGORY_COLOUR = "#4ADE80"
BORDER = "#334155"


# ============================================================
# FOXLOGI CATEGORY NAMES / ORDER
# ============================================================

CATEGORY_LABELS = {
    "smallarms": "Small Arms",
    "small arms": "Small Arms",

    "heavyarms": "Heavy Arms",
    "heavy arms": "Heavy Arms",

    "heavyammo": "Heavy Ammunition",
    "heavy ammo": "Heavy Ammunition",
    "heavy ammunition": "Heavy Ammunition",

    "utility": "Utility",
    "supplies": "Supplies",
    "resources": "Resources",
    "medical": "Medical",
    "uniforms": "Uniforms",

    "vehicles": "Vehicles",
    "cratedvehicles": "Vehicles",
    "crated vehicles": "Vehicles",

    "structures": "Structures",
    "cratedstructures": "Structures",
    "crated structures": "Structures",
}

CATEGORY_ORDER = [
    "Small Arms",
    "Heavy Arms",
    "Heavy Ammunition",
    "Utility",
    "Medical",
    "Supplies",
    "Resources",
    "Uniforms",
    "Vehicles",
    "Structures",
    "Other",
]


# ============================================================
# FONTS
# ============================================================

def load_font(size, bold=False):
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)

    return ImageFont.load_default()


FONT_TITLE = load_font(36, bold=True)
FONT_SUBTITLE = load_font(18)
FONT_SECTION = load_font(25, bold=True)
FONT_CARD_TITLE = load_font(20, bold=True)
FONT_CATEGORY = load_font(16, bold=True)
FONT_BODY = load_font(17)
FONT_SMALL = load_font(15)


def font_height(font):
    box = font.getbbox("Ag")
    return box[3] - box[1]


# ============================================================
# HTTP
# ============================================================

def get_json(url, headers=None):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **(headers or {}),
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"GET {url} returned HTTP {exc.code}: {detail}"
        ) from exc


def post_discord_image(content, image_path):
    """
    Upload the generated PNG to the Discord webhook as a file attachment.
    """

    boundary = "----NOBLEFoxlogiDashboardBoundary"

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    payload_json = json.dumps(
        {
            "content": content,
            "allowed_mentions": {"parse": []},
        }
    ).encode("utf-8")

    body = io.BytesIO()

    def line(value=b""):
        body.write(value)
        body.write(b"\r\n")

    boundary_bytes = boundary.encode("utf-8")

    # JSON payload
    line(b"--" + boundary_bytes)
    line(b'Content-Disposition: form-data; name="payload_json"')
    line(b"Content-Type: application/json")
    line()
    line(payload_json)

    # PNG attachment
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
        DISCORD_WEBHOOK_URL,
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT,
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


# ============================================================
# FOXLOGI HELPERS
# ============================================================

def number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def record_name(record, fallback):
    if isinstance(record, dict):
        return str(
            record.get("name")
            or record.get("title")
            or record.get("code_name")
            or fallback
        )

    return fallback


def location_name(locations, location_id):
    record = locations.get(str(location_id)) or locations.get(location_id)
    return record_name(record, f"Location {location_id}")


def item_record(items, item_id):
    record = items.get(str(item_id)) or items.get(item_id)
    return record if isinstance(record, dict) else {}


def item_name(items, item_id):
    return record_name(
        item_record(items, item_id),
        f"Item {item_id}",
    )


def category_name(items, item_id, fallback="Other"):
    record = item_record(items, item_id)

    raw = str(record.get("category") or "").strip()

    if not raw:
        return fallback

    key = raw.lower().replace("_", " ")
    compact = key.replace(" ", "")

    return (
        CATEGORY_LABELS.get(key)
        or CATEGORY_LABELS.get(compact)
        or raw
    )


def category_sort_key(category):
    try:
        return (
            CATEGORY_ORDER.index(category),
            category.lower(),
        )

    except ValueError:
        return (
            len(CATEGORY_ORDER),
            category.lower(),
        )


def ellipsize(draw, text, font, max_width):
    """
    Shorten text with ... until it fits the available width.
    """

    text = str(text)

    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text

    while len(text) > 4:
        text = text[:-1]

        candidate = text.rstrip() + "..."

        if draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )[2] <= max_width:
            return candidate

    return "..."


# ============================================================
# TOP-3 DEMAND LOGIC
# ============================================================

def grouped_top_items(item_quantities, items, limit=3):
    """
    Group outstanding individual items by Foxlogi category,
    then return the 3 highest-demand items from each category.
    """

    grouped = {}

    for item_id, qty in item_quantities.items():
        qty = number(qty)

        if qty <= 0:
            continue

        category = category_name(items, item_id)

        grouped.setdefault(category, []).append(
            (
                item_name(items, item_id),
                qty,
            )
        )

    output = []

    for category in sorted(grouped, key=category_sort_key):
        all_items = grouped[category]

        ranked = sorted(
            all_items,
            key=lambda entry: (
                -entry[1],
                entry[0].lower(),
            ),
        )[:limit]

        output.append(
            {
                "category": category,
                "items": ranked,
                "total": sum(qty for _, qty in all_items),
            }
        )

    return output


# ============================================================
# BUILD TRANSPORT DATA
# ============================================================

def build_transport(planner, locations, items):
    output = []

    transport = planner.get("transport") or {}

    if not isinstance(transport, dict):
        return output

    for destination_id, source_map in transport.items():

        if not isinstance(source_map, dict):
            continue

        for source_id, groups in source_map.items():

            if not isinstance(groups, dict):
                continue

            manifest = {}

            for group in groups.values():

                if not isinstance(group, dict):
                    continue

                group_items = group.get("items") or {}

                if not isinstance(group_items, dict):
                    continue

                for item_id, qty in group_items.items():
                    item_key = str(item_id)

                    manifest[item_key] = (
                        manifest.get(item_key, 0)
                        + number(qty)
                    )

            total = sum(
                qty
                for qty in manifest.values()
                if qty > 0
            )

            if total <= 0:
                continue

            output.append(
                {
                    "title": (
                        f"{location_name(locations, source_id)}"
                        f" → "
                        f"{location_name(locations, destination_id)}"
                    ),
                    "total": total,
                    "categories": grouped_top_items(
                        manifest,
                        items,
                        limit=3,
                    ),
                }
            )

    return output


# ============================================================
# BUILD FACTORY DATA
# ============================================================

def build_factory(planner, locations, items):
    output = []

    craft = planner.get("craft") or {}

    if not isinstance(craft, dict):
        return output

    for location_id, payload in craft.items():

        if not isinstance(payload, dict):
            continue

        requested = payload.get("items") or {}

        if not isinstance(requested, dict):
            continue

        total = sum(
            number(qty)
            for qty in requested.values()
            if number(qty) > 0
        )

        if total <= 0:
            continue

        output.append(
            {
                "title": location_name(
                    locations,
                    location_id,
                ),
                "total": total,
                "categories": grouped_top_items(
                    requested,
                    items,
                    limit=3,
                ),
            }
        )

    return output


# ============================================================
# BUILD MPF DATA
# ============================================================

def build_mpf(planner, locations, items):
    output = []

    mpf = planner.get("mpf") or {}

    if not isinstance(mpf, dict):
        return output

    for location_id, payload in mpf.items():

        requested = {}

        if isinstance(payload, dict):
            candidate = (
                payload.get("items")
                or payload.get("total_request")
                or {}
            )

            if isinstance(candidate, dict):
                requested = candidate

        total = sum(
            number(qty)
            for qty in requested.values()
            if number(qty) > 0
        )

        if total <= 0:
            continue

        output.append(
            {
                "title": location_name(
                    locations,
                    location_id,
                ),
                "total": total,
                "categories": grouped_top_items(
                    requested,
                    items,
                    limit=3,
                ),
            }
        )

    return output


# ============================================================
# BUILD REFINERY DATA
# ============================================================

def build_refinery(planner, locations, items):
    output = []

    resource = planner.get("resource") or {}

    if not isinstance(resource, dict):
        return output

    for location_id, payload in resource.items():

        if not isinstance(payload, dict):
            continue

        entries = []

        for item_id, detail in sorted(
            payload.items(),
            key=lambda entry: item_name(
                items,
                entry[0],
            ).lower(),
        ):

            name = item_name(items, item_id)

            if isinstance(detail, dict):
                amount = number(detail.get("crates"))
                output_amount = number(detail.get("output"))
                raw_input = number(detail.get("input"))

            else:
                amount = number(detail)
                output_amount = 0
                raw_input = 0

            # Important:
            # Refinery numbers are deliberately NOT labelled "crates".
            if amount > 0:
                value = f"{amount:,}"

            elif output_amount > 0:
                value = f"{output_amount:,}"

            elif raw_input > 0:
                value = f"{raw_input:,} raw required"

            else:
                continue

            entries.append(
                (
                    name,
                    value,
                )
            )

        if entries:
            output.append(
                {
                    "title": location_name(
                        locations,
                        location_id,
                    ),
                    "entries": entries,
                }
            )

    return output


# ============================================================
# IMAGE LAYOUT CALCULATIONS
# ============================================================

def ranked_card_height(card_width, categories):
    padding = 16

    title_height = font_height(FONT_CARD_TITLE)
    small_height = font_height(FONT_SMALL)
    body_height = font_height(FONT_BODY)

    category_rows = max(
        1,
        math.ceil(len(categories) / 3),
    )

    tallest_category = max(
        (
            len(category.get("items", []))
            for category in categories
        ),
        default=1,
    )

    category_box_height = (
        12
        + font_height(FONT_CATEGORY)
        + 10
        + tallest_category * (body_height + 7)
        + 12
    )

    return (
        padding
        + title_height
        + 8
        + small_height
        + 18
        + category_rows * category_box_height
        + max(0, category_rows - 1) * 12
        + padding
    )


def refinery_card_height(entries):
    padding = 16

    body_height = font_height(FONT_BODY)

    rows = math.ceil(
        max(1, len(entries)) / 3
    )

    return (
        padding
        + font_height(FONT_CARD_TITLE)
        + 18
        + rows * (body_height + 10)
        + padding
    )


def ranked_panel_height(blocks, panel_width):
    if not blocks:
        return 100

    inner_width = panel_width - 36
    card_gap = 14

    card_width = (
        inner_width - card_gap
    ) // 2

    height = 65
    row_height = 0

    for index, block in enumerate(blocks):
        card_height = ranked_card_height(
            card_width,
            block.get("categories", []),
        )

        row_height = max(
            row_height,
            card_height,
        )

        if index % 2 == 1:
            height += row_height + card_gap
            row_height = 0

    if len(blocks) % 2 == 1:
        height += row_height + card_gap

    return height + 10


def refinery_panel_height(blocks, panel_width):
    if not blocks:
        return 100

    height = 65
    card_gap = 14
    row_height = 0

    for index, block in enumerate(blocks):
        card_height = refinery_card_height(
            block.get("entries", [])
        )

        row_height = max(
            row_height,
            card_height,
        )

        if index % 2 == 1:
            height += row_height + card_gap
            row_height = 0

    if len(blocks) % 2 == 1:
        height += row_height + card_gap

    return height + 10


# ============================================================
# DRAWING HELPERS
# ============================================================

def rounded_box(
    draw,
    box,
    fill,
    outline=BORDER,
    radius=18,
    width=1,
):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_header(draw):
    now = datetime.now(LONDON)

    draw.text(
        (MARGIN, MARGIN),
        "NOBLE FOXLOGI DASHBOARD",
        font=FONT_TITLE,
        fill=TEXT,
    )

    draw.text(
        (
            MARGIN,
            MARGIN + font_height(FONT_TITLE) + 10,
        ),
        (
            "Current outstanding logistics demand"
            f"  |  Updated {now:%d %b %Y %H:%M} London time"
        ),
        font=FONT_SUBTITLE,
        fill=MUTED,
    )


def draw_panel_title(
    draw,
    x,
    y,
    width,
    title,
    count_text=None,
):
    draw.text(
        (x, y),
        title,
        font=FONT_SECTION,
        fill=TEXT,
    )

    if count_text:
        box = draw.textbbox(
            (0, 0),
            count_text,
            font=FONT_SUBTITLE,
        )

        text_width = box[2] - box[0]

        draw.text(
            (
                x + width - text_width,
                y + 5,
            ),
            count_text,
            font=FONT_SUBTITLE,
            fill=ACCENT,
        )


# ============================================================
# DRAW FACTORY / TRANSPORT / MPF CARD
# ============================================================

def draw_ranked_card(
    draw,
    x,
    y,
    width,
    block,
):
    categories = block.get("categories", [])

    height = ranked_card_height(
        width,
        categories,
    )

    rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + height,
        ),
        fill=CARD_BG,
    )

    padding = 16

    cursor_x = x + padding
    cursor_y = y + padding

    title = ellipsize(
        draw,
        block.get("title", ""),
        FONT_CARD_TITLE,
        width - padding * 2,
    )

    draw.text(
        (cursor_x, cursor_y),
        title,
        font=FONT_CARD_TITLE,
        fill=TEXT,
    )

    cursor_y += (
        font_height(FONT_CARD_TITLE)
        + 8
    )

    draw.text(
        (cursor_x, cursor_y),
        f"{block.get('total', 0):,} crates total",
        font=FONT_SMALL,
        fill=ACCENT,
    )

    cursor_y += (
        font_height(FONT_SMALL)
        + 18
    )

    if not categories:
        draw.text(
            (cursor_x, cursor_y),
            "No outstanding tasks",
            font=FONT_BODY,
            fill=MUTED,
        )

        return height

    columns = 3
    category_gap = 10

    category_width = (
        width
        - padding * 2
        - category_gap * 2
    ) // columns

    tallest_category = max(
        (
            len(category.get("items", []))
            for category in categories
        ),
        default=1,
    )

    category_height = (
        12
        + font_height(FONT_CATEGORY)
        + 10
        + tallest_category
        * (font_height(FONT_BODY) + 7)
        + 12
    )

    for index, category in enumerate(categories):

        row = index // columns
        column = index % columns

        box_x = (
            cursor_x
            + column
            * (category_width + category_gap)
        )

        box_y = (
            cursor_y
            + row
            * (category_height + 12)
        )

        rounded_box(
            draw,
            (
                box_x,
                box_y,
                box_x + category_width,
                box_y + category_height,
            ),
            fill=INNER_BG,
            radius=12,
        )

        category_title = ellipsize(
            draw,
            category.get("category", ""),
            FONT_CATEGORY,
            category_width - 16,
        )

        draw.text(
            (
                box_x + 8,
                box_y + 8,
            ),
            category_title,
            font=FONT_CATEGORY,
            fill=CATEGORY_COLOUR,
        )

        item_y = (
            box_y
            + 8
            + font_height(FONT_CATEGORY)
            + 10
        )

        for item, qty in category.get(
            "items",
            [],
        ):
            qty_text = f"{qty:,}"

            qty_box = draw.textbbox(
                (0, 0),
                qty_text,
                font=FONT_BODY,
            )

            qty_width = (
                qty_box[2]
                - qty_box[0]
            )

            item_max_width = (
                category_width
                - 26
                - qty_width
            )

            item_display = ellipsize(
                draw,
                item,
                FONT_BODY,
                item_max_width,
            )

            draw.text(
                (
                    box_x + 8,
                    item_y,
                ),
                item_display,
                font=FONT_BODY,
                fill=TEXT,
            )

            draw.text(
                (
                    box_x
                    + category_width
                    - 8
                    - qty_width,
                    item_y,
                ),
                qty_text,
                font=FONT_BODY,
                fill=ACCENT,
            )

            item_y += (
                font_height(FONT_BODY)
                + 7
            )

    return height


# ============================================================
# DRAW REFINERY CARD
# ============================================================

def draw_refinery_card(
    draw,
    x,
    y,
    width,
    block,
):
    entries = block.get("entries", [])

    height = refinery_card_height(entries)

    rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + height,
        ),
        fill=CARD_BG,
    )

    padding = 16

    cursor_x = x + padding
    cursor_y = y + padding

    title = ellipsize(
        draw,
        block.get("title", ""),
        FONT_CARD_TITLE,
        width - padding * 2,
    )

    draw.text(
        (cursor_x, cursor_y),
        title,
        font=FONT_CARD_TITLE,
        fill=TEXT,
    )

    cursor_y += (
        font_height(FONT_CARD_TITLE)
        + 18
    )

    columns = 3
    gap = 12

    column_width = (
        width
        - padding * 2
        - gap * 2
    ) // columns

    for index, entry in enumerate(entries):

        name, value = entry

        row = index // columns
        column = index % columns

        entry_x = (
            cursor_x
            + column
            * (column_width + gap)
        )

        entry_y = (
            cursor_y
            + row
            * (font_height(FONT_BODY) + 10)
        )

        value_box = draw.textbbox(
            (0, 0),
            value,
            font=FONT_BODY,
        )

        value_width = (
            value_box[2]
            - value_box[0]
        )

        name_width = (
            column_width
            - value_width
            - 16
        )

        name_display = ellipsize(
            draw,
            name,
            FONT_BODY,
            name_width,
        )

        draw.text(
            (
                entry_x,
                entry_y,
            ),
            name_display,
            font=FONT_BODY,
            fill=TEXT,
        )

        draw.text(
            (
                entry_x
                + column_width
                - value_width,
                entry_y,
            ),
            value,
            font=FONT_BODY,
            fill=ACCENT,
        )

    return height


# ============================================================
# DRAW PANELS
# ============================================================

def draw_ranked_panel(
    draw,
    x,
    y,
    width,
    title,
    blocks,
):
    panel_height = ranked_panel_height(
        blocks,
        width,
    )

    rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + panel_height,
        ),
        fill=PANEL_BG,
        width=2,
        radius=22,
    )

    draw_panel_title(
        draw,
        x + 18,
        y + 16,
        width - 36,
        title,
        (
            f"{len(blocks)} active"
            if blocks
            else None
        ),
    )

    cursor_y = (
        y
        + 16
        + font_height(FONT_SECTION)
        + 18
    )

    if not blocks:
        draw.text(
            (
                x + 18,
                cursor_y,
            ),
            "No outstanding tasks",
            font=FONT_BODY,
            fill=MUTED,
        )

        return panel_height

    inner_width = width - 36
    card_gap = 14

    card_width = (
        inner_width - card_gap
    ) // 2

    row_height = 0

    for index, block in enumerate(blocks):

        column = index % 2

        card_x = (
            x
            + 18
            + column
            * (card_width + card_gap)
        )

        card_height = draw_ranked_card(
            draw,
            card_x,
            cursor_y,
            card_width,
            block,
        )

        row_height = max(
            row_height,
            card_height,
        )

        if column == 1:
            cursor_y += (
                row_height
                + card_gap
            )

            row_height = 0

    return panel_height


def draw_refinery_panel(
    draw,
    x,
    y,
    width,
    blocks,
):
    panel_height = refinery_panel_height(
        blocks,
        width,
    )

    rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + panel_height,
        ),
        fill=PANEL_BG,
        width=2,
        radius=22,
    )

    draw_panel_title(
        draw,
        x + 18,
        y + 16,
        width - 36,
        "REFINERY",
        (
            f"{len(blocks)} active"
            if blocks
            else None
        ),
    )

    cursor_y = (
        y
        + 16
        + font_height(FONT_SECTION)
        + 18
    )

    if not blocks:
        draw.text(
            (
                x + 18,
                cursor_y,
            ),
            "No outstanding tasks",
            font=FONT_BODY,
            fill=MUTED,
        )

        return panel_height

    inner_width = width - 36
    card_gap = 14

    card_width = (
        inner_width - card_gap
    ) // 2

    row_height = 0

    for index, block in enumerate(blocks):

        column = index % 2

        card_x = (
            x
            + 18
            + column
            * (card_width + card_gap)
        )

        card_height = draw_refinery_card(
            draw,
            card_x,
            cursor_y,
            card_width,
            block,
        )

        row_height = max(
            row_height,
            card_height,
        )

        if column == 1:
            cursor_y += (
                row_height
                + card_gap
            )

            row_height = 0

    return panel_height


# ============================================================
# GENERATE DASHBOARD
# ============================================================

def render_dashboard(
    transport,
    factory,
    refinery,
    mpf,
):
    panel_width = (
        CANVAS_WIDTH
        - MARGIN * 2
        - PANEL_GAP
    ) // 2

    transport_height = ranked_panel_height(
        transport,
        panel_width,
    )

    factory_height = ranked_panel_height(
        factory,
        panel_width,
    )

    refinery_height = refinery_panel_height(
        refinery,
        panel_width,
    )

    mpf_height = ranked_panel_height(
        mpf,
        panel_width,
    )

    header_height = 110

    top_row_height = max(
        transport_height,
        factory_height,
    )

    bottom_row_height = max(
        refinery_height,
        mpf_height,
    )

    canvas_height = (
        MARGIN
        + header_height
        + top_row_height
        + PANEL_GAP
        + bottom_row_height
        + MARGIN
    )

    canvas_height = max(
        canvas_height,
        900,
    )

    image = Image.new(
        "RGB",
        (
            CANVAS_WIDTH,
            canvas_height,
        ),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(image)

    draw_header(draw)

    panel_y = (
        MARGIN
        + header_height
    )

    left_x = MARGIN

    right_x = (
        MARGIN
        + panel_width
        + PANEL_GAP
    )

    draw_ranked_panel(
        draw,
        left_x,
        panel_y,
        panel_width,
        "TRANSPORT",
        transport,
    )

    draw_ranked_panel(
        draw,
        right_x,
        panel_y,
        panel_width,
        "FACTORY",
        factory,
    )

    second_row_y = (
        panel_y
        + top_row_height
        + PANEL_GAP
    )

    draw_refinery_panel(
        draw,
        left_x,
        second_row_y,
        panel_width,
        refinery,
    )

    draw_ranked_panel(
        draw,
        right_x,
        second_row_y,
        panel_width,
        "MPF",
        mpf,
    )

    footer = (
        "Top 3 outstanding items shown per category"
        " | Source: Foxlogi"
    )

    footer_box = draw.textbbox(
        (0, 0),
        footer,
        font=FONT_SMALL,
    )

    footer_width = (
        footer_box[2]
        - footer_box[0]
    )

    draw.text(
        (
            CANVAS_WIDTH
            - MARGIN
            - footer_width,
            canvas_height
            - MARGIN
            + 3,
        ),
        footer,
        font=FONT_SMALL,
        fill=MUTED,
    )

    image.save(
        OUTPUT_IMAGE,
        format="PNG",
        optimize=True,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    planner = get_json(
        FOXLOGI_URL,
        headers={
            "Authorization":
                f"Bearer {FOXLOGI_API_KEY}"
        },
    )

    if not isinstance(planner, dict):
        raise RuntimeError(
            "Foxlogi returned an unexpected planner response"
        )

    locations = (
        planner.get("locations")
        if isinstance(
            planner.get("locations"),
            dict,
        )
        else {}
    )

    items = (
        planner.get("items")
        if isinstance(
            planner.get("items"),
            dict,
        )
        else {}
    )

    transport = build_transport(
        planner,
        locations,
        items,
    )

    factory = build_factory(
        planner,
        locations,
        items,
    )

    refinery = build_refinery(
        planner,
        locations,
        items,
    )

    mpf = build_mpf(
        planner,
        locations,
        items,
    )

    render_dashboard(
        transport,
        factory,
        refinery,
        mpf,
    )

    now = datetime.now(LONDON)

    post_discord_image(
        (
            "**NOBLE FOXLOGI DASHBOARD**"
            f" — Updated {now:%H:%M}"
        ),
        OUTPUT_IMAGE,
    )

    populated = (
        len(transport)
        + len(factory)
        + len(refinery)
        + len(mpf)
    )

    print(
        "Posted custom logistics dashboard "
        f"with {populated} active cards."
    )


if __name__ == "__main__":
    main()
