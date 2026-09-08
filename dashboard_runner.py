#!/usr/bin/env python3

import foxlogi_bot as bot


_original_draw_ranked_panel = bot.draw_ranked_panel


def draw_ranked_panel_with_wide_factory_mpf(
    draw,
    x,
    y,
    width,
    title,
    blocks,
):
    """
    Keep Transport using the standard two-card layout, but allow an odd
    Factory or MPF card to span the full panel width so unused space is not
    left blank.
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
            (
                x + 18,
                cursor_y,
            ),
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

        # When only one card remains, use the full width of the panel.
        if remaining == 1:
            bot.draw_ranked_card(
                draw,
                x + 18,
                cursor_y,
                inner_width,
                blocks[index],
            )
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


bot.draw_ranked_panel = draw_ranked_panel_with_wide_factory_mpf


if __name__ == "__main__":
    bot.main()
