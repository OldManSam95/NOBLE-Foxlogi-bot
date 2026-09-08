#!/usr/bin/env python3

import math

from PIL import Image, ImageDraw

import foxlogi_bot as bot


def category_column_count(card_width):
    """Use wider category boxes on narrower cards."""
    return 2 if card_width < 500 else 3


def category_total_card_height(card_width, categories):
    """Compact card height when only category crate totals are shown."""
    padding = 16
    columns = category_column_count(card_width)
    rows = max(1, math.ceil(len(categories) / columns))

    category_box_height = (
        12
        + bot.font_height(bot.FONT_CATEGORY)
        + 8
        + bot.font_height(bot.FONT_BODY)
        + 12
    )

    return (
        padding
        + bot.font_height(bot.FONT_CARD_TITLE)
        + 8
        + bot.font_height(bot.FONT_SMALL)
        + 18
        + rows * category_box_height
        + max(0, rows - 1) * 12
        + padding
    )


def draw_category_total_card(draw, x, y, width, block):
    """Draw Transport/Factory/MPF cards using category totals only."""
    categories = block.get("categories", [])
    height = category_total_card_height(width, categories)

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

    cursor_y += bot.font_height(bot.FONT_CARD_TITLE) + 8

    draw.text(
        (cursor_x, cursor_y),
        f"{block.get('total', 0):,} crates total",
        font=bot.FONT_SMALL,
        fill=bot.ACCENT,
    )

    cursor_y += bot.font_height(bot.FONT_SMALL) + 18

    if not categories:
        draw.text(
            (cursor_x, cursor_y),
            "No outstanding tasks",
            font=bot.FONT_BODY,
            fill=bot.MUTED,
        )
        return height

    columns = category_column_count(width)
    category_gap = 10

    category_width = (
        width - padding * 2 - category_gap * (columns - 1)
    ) // columns

    category_height = (
        12
        + bot.font_height(bot.FONT_CATEGORY)
        + 8
        + bot.font_height(bot.FONT_BODY)
        + 12
    )

    for index, category in enumerate(categories):
        row = index // columns
        column = index % columns

        box_x = cursor_x + column * (category_width + category_gap)
        box_y = cursor_y + row * (category_height + 12)

        bot.rounded_box(
            draw,
            (box_x, box_y, box_x + category_width, box_y + category_height),
            fill=bot.INNER_BG,
            radius=12,
        )

        category_title = bot.ellipsize(
            draw,
            category.get("category", ""),
            bot.FONT_CATEGORY,
            category_width - 16,
        )

        draw.text(
            (box_x + 8, box_y + 8),
            category_title,
            font=bot.FONT_CATEGORY,
            fill=bot.CATEGORY_COLOUR,
        )

        draw.text(
            (
                box_x + 8,
                box_y + 8 + bot.font_height(bot.FONT_CATEGORY) + 8,
            ),
            f"{category.get('total', 0):,} crates",
            font=bot.FONT_BODY,
            fill=bot.ACCENT,
        )

    return height


def transport_panel_height(blocks, panel_width):
    """Transport cards are stacked vertically, one full-width card per row."""
    if not blocks:
        return 100

    inner_width = panel_width - 36
    card_gap = 14
    height = 65

    for block in blocks:
        height += category_total_card_height(
            inner_width,
            block.get("categories", []),
        ) + card_gap

    return height + 10


def standard_ranked_panel_height(blocks, panel_width):
    """Factory and MPF use two cards per row, with odd final card full width."""
    if not blocks:
        return 100

    inner_width = panel_width - 36
    card_gap = 14
    half_card_width = (inner_width - card_gap) // 2
    height = 65
    index = 0

    while index < len(blocks):
        remaining = len(blocks) - index

        if remaining == 1:
            card_height = category_total_card_height(
                inner_width,
                blocks[index].get("categories", []),
            )
            height += card_height + card_gap
            break

        left_height = category_total_card_height(
            half_card_width,
            blocks[index].get("categories", []),
        )
        right_height = category_total_card_height(
            half_card_width,
            blocks[index + 1].get("categories", []),
        )
        height += max(left_height, right_height) + card_gap
        index += 2

    return height + 10


def draw_transport_panel(draw, x, y, width, blocks, forced_height=None):
    panel_height = (
        forced_height
        if forced_height is not None
        else transport_panel_height(blocks, width)
    )

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
        "TRANSPORT",
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

    for block in blocks:
        card_height = draw_category_total_card(
            draw,
            x + 18,
            cursor_y,
            inner_width,
            block,
        )
        cursor_y += card_height + card_gap

    return panel_height


def draw_standard_ranked_panel(draw, x, y, width, title, blocks):
    panel_height = standard_ranked_panel_height(blocks, width)

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
        title,
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
            card_height = draw_category_total_card(
                draw,
                x + 18,
                cursor_y,
                inner_width,
                blocks[index],
            )
            cursor_y += card_height + card_gap
            break

        left_height = draw_category_total_card(
            draw,
            x + 18,
            cursor_y,
            half_card_width,
            blocks[index],
        )

        right_height = draw_category_total_card(
            draw,
            x + 18 + half_card_width + card_gap,
            cursor_y,
            half_card_width,
            blocks[index + 1],
        )

        cursor_y += max(left_height, right_height) + card_gap
        index += 2

    return panel_height


def draw_refinery_panel(draw, x, y, width, blocks):
    panel_height = bot.refinery_panel_height(blocks, width)

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
    card_width = (inner_width - card_gap) // 2
    row_height = 0

    for index, block in enumerate(blocks):
        column = index % 2
        card_x = x + 18 + column * (card_width + card_gap)
        card_height = bot.draw_refinery_card(
            draw,
            card_x,
            cursor_y,
            card_width,
            block,
        )
        row_height = max(row_height, card_height)
        if column == 1:
            cursor_y += row_height + card_gap
            row_height = 0

    return panel_height


def render_dashboard_custom(transport, factory, refinery, mpf):
    panel_width = (bot.CANVAS_WIDTH - bot.MARGIN * 2 - bot.PANEL_GAP) // 2

    right_factory_h = standard_ranked_panel_height(factory, panel_width)
    right_mpf_h = standard_ranked_panel_height(mpf, panel_width)
    right_refinery_h = bot.refinery_panel_height(refinery, panel_width)

    right_column_total = (
        right_factory_h
        + bot.PANEL_GAP
        + right_mpf_h
        + bot.PANEL_GAP
        + right_refinery_h
    )

    left_transport_h = max(
        transport_panel_height(transport, panel_width),
        right_column_total,
    )

    header_height = 110
    canvas_height = (
        bot.MARGIN
        + header_height
        + max(left_transport_h, right_column_total)
        + bot.MARGIN
    )
    canvas_height = max(canvas_height, 900)

    image = Image.new(
        "RGB",
        (bot.CANVAS_WIDTH, canvas_height),
        bot.BACKGROUND,
    )
    draw = ImageDraw.Draw(image)

    bot.draw_header(draw)

    panel_y = bot.MARGIN + header_height
    left_x = bot.MARGIN
    right_x = bot.MARGIN + panel_width + bot.PANEL_GAP

    draw_transport_panel(
        draw,
        left_x,
        panel_y,
        panel_width,
        transport,
        forced_height=left_transport_h,
    )

    draw_standard_ranked_panel(
        draw,
        right_x,
        panel_y,
        panel_width,
        "FACTORY",
        factory,
    )

    mpf_y = panel_y + right_factory_h + bot.PANEL_GAP
    draw_standard_ranked_panel(
        draw,
        right_x,
        mpf_y,
        panel_width,
        "MPF",
        mpf,
    )

    refinery_y = mpf_y + right_mpf_h + bot.PANEL_GAP
    draw_refinery_panel(
        draw,
        right_x,
        refinery_y,
        panel_width,
        refinery,
    )

    footer = "Outstanding crates shown by category | Source: Foxlogi"
    footer_box = draw.textbbox((0, 0), footer, font=bot.FONT_SMALL)
    footer_width = footer_box[2] - footer_box[0]

    draw.text(
        (
            image.width - bot.MARGIN - footer_width,
            image.height - bot.MARGIN + 3,
        ),
        footer,
        font=bot.FONT_SMALL,
        fill=bot.MUTED,
    )

    image.save(
        bot.OUTPUT_IMAGE,
        format="PNG",
        optimize=True,
    )


bot.ranked_card_height = category_total_card_height
bot.draw_ranked_card = draw_category_total_card
bot.render_dashboard = render_dashboard_custom


if __name__ == "__main__":
    bot.main()
