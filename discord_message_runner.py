#!/usr/bin/env python3

import refinery_runner as current


bot = current.bot
_original_post_discord_image = bot.post_discord_image


def post_discord_image_with_foxlogi_link(content, image_path):
    """Add a clear Foxlogi call-to-action to the Discord message text."""
    message = (
        f"{content}\n\n"
        "For more information and the full logistics planner, visit Foxlogi: "
        "https://foxlogi.com/"
    )
    return _original_post_discord_image(message, image_path)


bot.post_discord_image = post_discord_image_with_foxlogi_link


if __name__ == "__main__":
    bot.main()
