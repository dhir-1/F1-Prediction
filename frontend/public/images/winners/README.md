# Winner Images

This directory holds optional local winner photos for the Race Archive (`/history`) page.

## Naming Convention

Use the race slug from `backend/app/api/site_data.py`.

Examples:
- `australian-grand-prix.jpg`
- `chinese-grand-prix.jpg`
- `japanese-grand-prix.jpg`
- `miami-grand-prix.jpg`

If a local image is missing, the archive falls back automatically to the live winner spotlight layout using team color styling and driver headshot metadata from FastF1.
