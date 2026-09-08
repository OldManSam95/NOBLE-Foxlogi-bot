#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.request

FOXLOGI_URL = "https://foxlogi.com/api/logistic/planner/"
FOXLOGI_API_KEY = os.environ["FOXLOGI_API_KEY"].strip()
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"].strip()
USER_AGENT = "NOBLE-Foxlogi-Bot-Test/0.2"

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


def get_json(url, headers=None):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"GET {url} returned HTTP {exc.code}: {detail}") from exc


def post_discord(content):
    payload = json.dumps({"content": content, "allowed_mentions": {"parse": []}}).encode("utf-8")
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Discord returned HTTP {exc.code}: {detail}") from exc


def record_name(record, fallback):
    if isinstance(record, dict):
        return str(record.get("name") or record.get("title") or record.get("code_name") or fallback)
    return fallback


def location_name(locations, location_id):
    return record_name(locations.get(str(location_id)) or locations.get(location_id), f"Location {location_id}")


def item_record(items, item_id):
    record = items.get(str(item_id)) or items.get(item_id)
    return record if isinstance(record, dict) else {}


def category_name(items, item_id, fallback="Other"):
    record = item_record(items, item_id)
    raw = str(record.get("category") or "").strip()
    if not raw:
        return fallback
    key = raw.lower().replace("_", " ")
    compact = key.replace(" ", "")
    return CATEGORY_LABELS.get(key) or CATEGORY_LABELS.get(compact) or raw


def number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def category_sort_key(category):
    try:
        return (CATEGORY_ORDER.index(category), category.lower())
    except ValueError:
        return (len(CATEGORY_ORDER), category.lower())


def aggregate_categories(item_quantities, items, fallback="Other"):
    totals = {}
    for item_id, qty in item_quantities.items():
        qty = number(qty)
        if qty <= 0:
            continue
        category = category_name(items, item_id, fallback=fallback)
        totals[category] = totals.get(category, 0) + qty
    return sorted(totals.items(), key=lambda x: category_sort_key(x[0]))


def format_transport(planner, locations, items):
    lines = []
    transport = planner.get("transport") or {}
    if not isinstance(transport, dict):
        return lines

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
                    manifest[str(item_id)] = manifest.get(str(item_id), 0) + number(qty)

            categories = aggregate_categories(manifest, items)
            if not categories:
                continue

            source = location_name(locations, source_id)
            destination = location_name(locations, destination_id)
            total = sum(qty for _, qty in categories)
            lines.append(f"**{source} → {destination}** — {total:,} crates")
            for category, qty in categories:
                lines.append(f"• {category} — {qty:,} crates")
    return lines


def format_craft(planner, locations, items):
    lines = []
    craft = planner.get("craft") or {}
    if not isinstance(craft, dict):
        return lines

    for location_id, payload in craft.items():
        if not isinstance(payload, dict):
            continue
        requested = payload.get("items") or {}
        if not isinstance(requested, dict):
            continue
        categories = aggregate_categories(requested, items)
        if not categories:
            continue

        lines.append(f"**{location_name(locations, location_id)}**")
        for category, qty in categories:
            lines.append(f"• {category} — {qty:,} crates")
    return lines


def format_refinery(planner, locations, items):
    lines = []
    resource = planner.get("resource") or {}
    if not isinstance(resource, dict):
        return lines

    for location_id, payload in resource.items():
        if not isinstance(payload, dict):
            continue

        categories = set()
        for item_id, detail in payload.items():
            active = False
            if isinstance(detail, dict):
                active = any(number(detail.get(key)) > 0 for key in ("crates", "output", "input"))
            else:
                active = number(detail) > 0
            if active:
                categories.add(category_name(items, item_id, fallback="Resources"))

        if categories:
            lines.append(f"**{location_name(locations, location_id)}**")
            for category in sorted(categories, key=category_sort_key):
                lines.append(f"• {category}")
    return lines


def format_mpf(planner, locations, items):
    lines = []
    mpf = planner.get("mpf") or {}
    if not isinstance(mpf, dict):
        return lines

    for location_id, payload in mpf.items():
        categories = []
        if isinstance(payload, dict):
            requested = payload.get("items") or payload.get("total_request") or {}
            if isinstance(requested, dict):
                categories = aggregate_categories(requested, items)

        lines.append(f"**{location_name(locations, location_id)}**")
        if categories:
            for category, qty in categories:
                lines.append(f"• {category} — {qty:,} crates")
        else:
            lines.append("• MPF work required")
    return lines


def build_message(planner):
    if not isinstance(planner, dict):
        raise RuntimeError("Foxlogi returned an unexpected planner response")

    locations = planner.get("locations") if isinstance(planner.get("locations"), dict) else {}
    items = planner.get("items") if isinstance(planner.get("items"), dict) else {}

    sections = [
        ("🚛 TRANSPORT", format_transport(planner, locations, items)),
        ("🏭 FACTORY", format_craft(planner, locations, items)),
        ("⚗️ REFINERY", format_refinery(planner, locations, items)),
        ("🏗️ MPF", format_mpf(planner, locations, items)),
    ]

    timestamp = int(time.time())
    lines = [
        "# 🚚 NOBLE FOXLOGI TEST",
        f"*Current logistics tasks • Generated <t:{timestamp}:R>*",
        "",
    ]

    task_count = 0
    for heading, body in sections:
        if not body:
            continue
        task_count += 1
        lines.extend([f"## {heading}", *body, ""])

    if task_count == 0:
        lines.extend(["✅ **No outstanding logistics tasks were returned by Foxlogi.**", ""])

    lines.append("-# Test post • Source: Foxlogi")
    return "\n".join(lines).strip()


def split_for_discord(text, limit=1900):
    chunks = []
    current = ""
    for line in text.splitlines():
        candidate = line if not current else current + "\n" + line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = line
    if current:
        chunks.append(current)
    return chunks


def main():
    planner = get_json(
        FOXLOGI_URL,
        headers={"Authorization": f"Bearer {FOXLOGI_API_KEY}"},
    )
    message = build_message(planner)
    chunks = split_for_discord(message)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            chunk = f"**Part {index}/{len(chunks)}**\n{chunk}"
        post_discord(chunk)

    print(f"Posted {len(chunks)} Discord message(s).")


if __name__ == "__main__":
    main()
