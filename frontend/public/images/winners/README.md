# Winner Images

This directory holds the images for the race winners shown on the Race Archive (/history) page.

## Naming Convention

Images should be named according to the `winnerImage` field defined in `backend/app/data/season.py`. 

For example:
- `australian-grand-prix-2026.jpg`
- `chinese-grand-prix-2026.jpg`
- `japanese-grand-prix-2026.jpg`

If an image is missing, the frontend will automatically gracefully degrade to a solid color gradient based on the winning team's colors.
