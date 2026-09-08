# NOBLE Foxlogi Bot

Test project for posting the current Foxlogi logistics planner to a Discord channel.

## Current test mode

- Manual GitHub Actions trigger only.
- Reads `https://foxlogi.com/api/logistic/planner/` using `FOXLOGI_API_KEY`.
- Posts to the Discord webhook stored as `DISCORD_WEBHOOK_URL`.
- Does not modify Foxlogi data.
- Does not run on a schedule yet.

## Required repository secrets

- `FOXLOGI_API_KEY`
- `DISCORD_WEBHOOK_URL`

## Run the test

Open **Actions → Test Foxlogi Discord Post → Run workflow**.
