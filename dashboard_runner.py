#!/usr/bin/env python3

import math

from PIL import Image, ImageDraw

import foxlogi_bot as bot


_original_draw_ranked_panel = bot.draw_ranked_panel
_original_render_dashboard = bot.render_dashboard


def category_column_count(card_width):
    """Use wider category boxes on narrower Transport cards."""
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


def draw_category_total_card(
    draw,
    x,
    y,
    width,
    block,
):
    """Draw Transport/Factory/MPF using category totals only."""
    categories = block.get("categories", [])
    height = category_total_card_height(width, categories)

    bot.rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + height,
        ),
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

    cursor_y += (
        bot.font_height(bot.FONT_CARD_TITLE)
        + 8
    )

    draw.text(
        (cursor_x, cursor_y),
        f"{block.get('total', 0):,} crates total",
        font=bot.FONT_SMALL,
        fill=bot.ACCENT,
    )

    cursor_y += (
        bot.font_height(bot.FONT_SMALL)
        + 18
    )

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
        width
        - padding * 2
        - category_gap * (columns - 1)
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

        box_x = (
            cursor_x
            + column * (category_width + category_gap)
        )

        box_y = (
            cursor_y
            + row * (category_height + 12)
        )

        bot.rounded_box(
            draw,
            (
                box_x,
                box_y,
                box_x + category_width,
                box_y + category_height,
            ),
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
                box_y
                + 8
                + bot.font_height(bot.FONT_CATEGORY)
                + 8,
            ),
            f"{category.get('total', 0):,} crates",
            font=bot.FONT_BODY,
            fill=bot.ACCENT,
        )

    return height


def draw_ranked_panel_with_wide_factory_mpf(
    draw,
    x,
    y,
    width,
    title,
    blocks,
):
    """
    Keep Transport using two cards per row, but let an odd Factory or MPF
    card span the full panel width.
    """

    if title not in {"FACTORY", "MPF"}:
        return _original_draw_ranked_panel(
            draw,
            x,
            y,
            width,
            title,
            blocks,
        )

    panel_height = bot.ranked_panel_height(
        blocks,
        width,
    )

    bot.rounded_box(
        draw,
        (
            x,
            y,
            x + width,
            y + panel_height,
        ),
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
        (
            f"{len(blocks)} active"
            if blocks
            else None
        ),
    )

    cursor_y = (
        y
        + 16
        + bot.font_height(bot.FONT_SECTION)
        + 18
    )

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
    half_card_width = (
        inner_width - card_gap
    ) // 2

    index = 0

    while index < len(blocks):
        remaining = len(blocks) - index

        if remaining == 1:
            card_height = bot.draw_ranked_card(
                draw,
                x + 18,
                cursor_y,
                inner_width,
                blocks[index],
            )
            cursor_y += card_height + card_gap
            break

        left_height = bot.draw_ranked_card(
            draw,
            x + 18,
            cursor_y,
            half_card_width,
            blocks[index],
        )

        right_height = bot.draw_ranked_card(
            draw,
            x + 18 + half_card_width + card_gap,
            cursor_y,
            half_card_width,
            blocks[index + 1],
        )

        cursor_y += (
            max(left_height, right_height)
            + card_gap
        )
        index += 2

    return panel_height


def render_dashboard_with_updated_footer(
    transport,
    factory,
    refinery,
    mpf,
):
    """Render normally, then replace the old top-3 footer text."""
    _original_render_dashboard(
        transport,
        factory,
        refinery,
        mpf,
    )

    image = Image.open(bot.OUTPUT_IMAGE).convert("RGB")
    draw = ImageDraw.Draw(image)

    clear_top = image.height - bot.MARGIN - 4
    draw.rectangle(
        (
            0,
            clear_top,
            image.width,
            image.height,
        ),
        fill=bot.BACKGROUND,
    )

    footer = "Outstanding crates shown by category | Source: Foxlogi"
    footer_box = draw.textbbox(
        (0, 0),
        footer,
        font=bot.FONT_SMALL,
    )
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
bot.draw_ranked_panel = draw_ranked_panel_with_wide_factory_mpf
bot.render_dashboard = render_dashboard_with_updated_footer


if __name__ == "__main__":
    bot.main()
