#!/usr/bin/env python3

import math

import dashboard_runner as dash


bot = dash.bot


# ============================================================
# REFINERY MATERIAL BOXES
# ============================================================


def refinery_material_card_height(card_width, entries):
    """Match the compact category-box layout used elsewhere on the dashboard."""
    padding = 16
    columns = dash.category_column_count(card_width)
    rows = max(1, math.ceil(len(entries) / columns))

    material_box_height = (
        12
        + bot.font_height(bot.FONT_CATEGORY)
        + 8
        + bot.font_height(bot.FONT_BODY)
        + 12
    )

    return (
        padding
        + bot.font_height(bot.FONT_CARD_TITLE)
        + 18
        + rows * material_box_height
        + max(0, rows - 1) * 12
        + padding
    )


def draw_refinery_material_card(draw, x, y, width, block):
    """Draw each refinery material as its own white metric box."""
    entries = block.get("entries", [])
    height = refinery_material_card_height(width, entries)

    bot.rounded_box(
        draw,
        (x, y, x + width, y + height),
        fill=bot.CARD_BG,
    )

    padding = 16
    cursor_x = x + padding
    cursor_y = y + padding

    title = bot.ellipsize(
        draw,
        block.get("title", ""),
        bot.FONT_CARD_TITLE,
        width - padding * 2,
    )

    draw.text(
        (cursor_x, cursor_y),
        title,
        font=bot.FONT_CARD_TITLE,
        fill=bot.TEXT,
    )

    cursor_y += bot.font_height(bot.FONT_CARD_TITLE) + 18

    if not entries:
        draw.text(
            (cursor_x, cursor_y),
            "No outstanding tasks",
            font=bot.FONT_BODY,
            fill=bot.MUTED,
        )
        return height

    columns = dash.category_column_count(width)
    gap = 10
    box_width = (width - padding * 2 - gap * (columns - 1)) // columns

    box_height = (
        12
        + bot.font_height(bot.FONT_CATEGORY)
        + 8
        + bot.font_height(bot.FONT_BODY)
        + 12
    )

    for index, (name, value) in enumerate(entries):
        row = index // columns
        column = index % columns

        box_x = cursor_x + column * (box_width + gap)
        box_y = cursor_y + row * (box_height + 12)

        bot.rounded_box(
            draw,
            (box_x, box_y, box_x + box_width, box_y + box_height),
            fill=bot.INNER_BG,
            outline=bot.TEXT,
            radius=12,
        )

        material_name = bot.ellipsize(
            draw,
            name,
            bot.FONT_CATEGORY,
            box_width - 16,
        )

        draw.text(
            (box_x + 8, box_y + 8),
            material_name,
            font=bot.FONT_CATEGORY,
            fill=bot.TEXT,
        )

        draw.text(
            (
                box_x + 8,
                box_y + 8 + bot.font_height(bot.FONT_CATEGORY) + 8,
            ),
            str(value),
            font=bot.FONT_BODY,
            fill=bot.TEXT,
        )

    return height


def refinery_panel_height(blocks, panel_width):
    """Size the refinery panel using the new material boxes."""
    if not blocks:
        return 100

    inner_width = panel_width - 36
    card_gap = 14
    half_card_width = (inner_width - card_gap) // 2
    height = 65
    index = 0

    while index < len(blocks):
        remaining = len(blocks) - index

        # Let an odd final refinery location use the full panel width.
        if remaining == 1:
            height += refinery_material_card_height(
                inner_width,
                blocks[index].get("entries", []),
            ) + card_gap
            break

        left_height = refinery_material_card_height(
            half_card_width,
            blocks[index].get("entries", []),
        )
        right_height = refinery_material_card_height(
            half_card_width,
            blocks[index + 1].get("entries", []),
        )

        height += max(left_height, right_height) + card_gap
        index += 2

    return height + 10


def draw_refinery_panel(draw, x, y, width, blocks):
    """Draw refinery locations using material boxes instead of text columns."""
    panel_height = refinery_panel_height(blocks, width)

    bot.rounded_box(
        draw,
        (x, y, x + width, y + panel_height),
        fill=bot.PANEL_BG,
        width=2,
        radius=22,
    )

    bot.draw_panel_title(
        draw,
        x + 18,
        y + 16,
        width - 36,
        "REFINERY",
        f"{len(blocks)} active" if blocks else None,
    )

    cursor_y = y + 16 + bot.font_height(bot.FONT_SECTION) + 18

    if not blocks:
        draw.text(
            (x + 18, cursor_y),
            "No outstanding tasks",
            font=bot.FONT_BODY,
            fill=bot.MUTED,
        )
        return panel_height

    inner_width = width - 36
    card_gap = 14
    half_card_width = (inner_width - card_gap) // 2
    index = 0

    while index < len(blocks):
        remaining = len(blocks) - index

        if remaining == 1:
            card_height = draw_refinery_material_card(
                draw,
                x + 18,
                cursor_y,
                inner_width,
                blocks[index],
            )
            cursor_y += card_height + card_gap
            break

        left_height = draw_refinery_material_card(
            draw,
            x + 18,
            cursor_y,
            half_card_width,
            blocks[index],
        )

        right_height = draw_refinery_material_card(
            draw,
            x + 18 + half_card_width + card_gap,
            cursor_y,
            half_card_width,
            blocks[index + 1],
        )

        cursor_y += max(left_height, right_height) + card_gap
        index += 2

    return panel_height


# Patch the current 2x Foxlogi-style renderer without changing its other sections.
bot.refinery_panel_height = refinery_panel_height
dash.draw_refinery_panel = draw_refinery_panel


if __name__ == "__main__":
    bot.main()
