#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

FOXLOGI_URL = "https://foxlogi.com/api/logistic/planner/"
FOXLOGI_API_KEY = os.environ["FOXLOGI_API_KEY"].strip()
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"].strip()
USER_AGENT = "NOBLE-Foxlogi-Bot-Test/0.8"

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


def post_discord(*, content=None, embeds=None):
    payload = {"allowed_mentions": {"parse": []}}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=data,
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


def item_name(items, item_id):
    return record_name(item_record(items, item_id), f"Item {item_id}")


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


def make_embed(title, fields, description=None):
    embed = {
        "title": title[:256],
        "fields": fields[:25],
        "footer": {"text": "Test post • Source: Foxlogi"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if description:
        embed["description"] = description[:4096]
    return embed


def three_column_fields(entries):
    """Pack label/value pairs into up to three dense inline fields with invisible headers."""
    if not entries:
        return []

    column_count = min(3, len(entries))
    base, extra = divmod(len(entries), column_count)
    fields = []
    start = 0

    for index in range(column_count):
        size = base + (1 if index < extra else 0)
        chunk = entries[start:start + size]
        start += size
        lines = [f"**{label}** — {value}" for label, value in chunk]
        fields.append({
            "name": "\u200b",
            "value": "\n".join(lines)[:1024],
            "inline": True,
        })

    return fields


def category_fields(categories):
    entries = [(category, f"{qty:,} crates") for category, qty in categories]
    return three_column_fields(entries)


def transport_embeds(planner, locations, items):
    embeds = []
    transport = planner.get("transport") or {}
    if not isinstance(transport, dict):
        return embeds

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
            embeds.append(
                make_embed(
                    f"🚛 TRANSPORT — {source} → {destination}",
                    category_fields(categories),
                    f"**{total:,} crates total**",
                )
            )
    return embeds


def factory_embeds(planner, locations, items):
    embeds = []
    craft = planner.get("craft") or {}
    if not isinstance(craft, dict):
        return embeds

    for location_id, payload in craft.items():
        if not isinstance(payload, dict):
            continue
        requested = payload.get("items") or {}
        if not isinstance(requested, dict):
            continue
        categories = aggregate_categories(requested, items)
        if not categories:
            continue
        total = sum(qty for _, qty in categories)
        embeds.append(
            make_embed(
                f"🏭 FACTORY — {location_name(locations, location_id)}",
                category_fields(categories),
                f"**{total:,} crates total**",
            )
        )
    return embeds


def refinery_embeds(planner, locations, items):
    embeds = []
    resource = planner.get("resource") or {}
    if not isinstance(resource, dict):
        return embeds

    for location_id, payload in resource.items():
        if not isinstance(payload, dict):
            continue

        entries = []
        for item_id, detail in sorted(payload.items(), key=lambda x: item_name(items, x[0]).lower()):
            name = item_name(items, item_id)
            if isinstance(detail, dict):
                amount = number(detail.get("crates"))
                output = number(detail.get("output"))
                raw_input = number(detail.get("input"))
            else:
                amount = number(detail)
                output = 0
                raw_input = 0

            if amount > 0:
                value = f"{amount:,}"
            elif output > 0:
                value = f"{output:,} output"
            elif raw_input > 0:
                value = f"{raw_input:,} raw required"
            else:
                continue

            entries.append((name, value))

        if entries:
            embeds.append(
                make_embed(
                    f"⚗️ REFINERY — {location_name(locations, location_id)}",
                    three_column_fields(entries),
                )
            )
    return embeds


def mpf_embeds(planner, locations, items):
    embeds = []
    mpf = planner.get("mpf") or {}
    if not isinstance(mpf, dict):
        return embeds

    for location_id, payload in mpf.items():
        categories = []
        if isinstance(payload, dict):
            requested = payload.get("items") or payload.get("total_request") or {}
            if isinstance(requested, dict):
                categories = aggregate_categories(requested, items)

        if categories:
            fields = category_fields(categories)
            total = sum(qty for _, qty in categories)
            description = f"**{total:,} crates total**"
        else:
            fields = [{"name": "\u200b", "value": "MPF work required", "inline": True}]
            description = None

        embeds.append(
            make_embed(
                f"🏗️ MPF — {location_name(locations, location_id)}",
                fields,
                description,
            )
        )
    return embeds


def embed_char_count(embed):
    total = len(embed.get("title", "")) + len(embed.get("description", ""))
    footer = embed.get("footer") or {}
    total += len(footer.get("text", ""))
    for field in embed.get("fields", []):
        total += len(field.get("name", "")) + len(field.get("value", ""))
    return total


def batch_embeds(embeds, max_embeds=10, max_chars=5500):
    batches = []
    current = []
    chars = 0

    for embed in embeds:
        size = embed_char_count(embed)
        if current and (len(current) >= max_embeds or chars + size > max_chars):
            batches.append(current)
            current = []
            chars = 0
        current.append(embed)
        chars += size

    if current:
        batches.append(current)
    return batches


def main():
    planner = get_json(
        FOXLOGI_URL,
        headers={"Authorization": f"Bearer {FOXLOGI_API_KEY}"},
    )
    if not isinstance(planner, dict):
        raise RuntimeError("Foxlogi returned an unexpected planner response")

    locations = planner.get("locations") if isinstance(planner.get("locations"), dict) else {}
    items = planner.get("items") if isinstance(planner.get("items"), dict) else {}

    embeds = []
    embeds.extend(transport_embeds(planner, locations, items))
    embeds.extend(factory_embeds(planner, locations, items))
    embeds.extend(refinery_embeds(planner, locations, items))
    embeds.extend(mpf_embeds(planner, locations, items))

    if not embeds:
        post_discord(content="✅ **NOBLE FOXLOGI TEST** — No outstanding logistics tasks were returned by Foxlogi.")
        print("Posted 1 Discord message with no outstanding tasks.")
        return

    batches = batch_embeds(embeds)
    for index, batch in enumerate(batches, start=1):
        content = "**🚚 NOBLE FOXLOGI TEST**"
        if len(batches) > 1:
            content += f" — Part {index}/{len(batches)}"
        post_discord(content=content, embeds=batch)

    print(f"Posted {len(embeds)} embed(s) across {len(batches)} Discord message(s).")


if __name__ == "__main__":
    main()
