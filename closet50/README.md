# CloSet50

A digital wardrobe: catalog your clothes, tag them, and put together outfits.
Built with Python + Flask, SQLite, and HTML/CSS/JavaScript with Jinja templates.

## Running it

```
pip install -r requirements.txt
flask run
```

Then open the link Flask prints (usually http://127.0.0.1:5000).
The database (`closet.db`) and the `static/uploads` folder are created automatically on first run.

## Files

| File | What it does |
|---|---|
| `app.py` | All the routes: accounts, closet, upload/edit/delete, generator, builder, saved outfits |
| `helpers.py` | `login_required`, image saving + background removal, weather lookup, outfit rules |
| `schema.sql` | Tables: `users`, `items`, `outfits`, `outfit_items`, `wear_log` |
| `templates/` | Jinja pages (all extend `layout.html`, like Finance) |
| `static/styles.css` | Styling, including the Pinterest-style closet grid |
| `static/script.js` | Shows the right "style" choices per clothing type, photo preview, live outfit preview in the builder |

## Features (from the project outline)

- **Accounts**: username + password (hashed). Password reset uses a security question chosen at sign up.
- **Upload**: .png/.jpg photos, tagged with clothing type + style (tops: long sleeves / short sleeves / tank top; bottoms: shorts / pants / skirt; dress; shoes; outerwear: thick / light), color, occasion (multi-select) and season (multi-select).
- **Remove background**: uses `rembg` if installed, otherwise a simple "paint bucket" fill from the photo's corners (works best on a plain background).
- **Closet view**: grid filtered by type, occasion and season; edit tags or remove items.
- **Outfit generator**: pick an occasion and season, or enter a temperature / city. Builds top + bottom + shoes, or dress + shoes, plus a jacket when it's cold, chosen randomly. Shows "You're missing: ___" when there aren't enough matching clothes.
- **Daily weather**: uses the free Open-Meteo API (no key needed).
  - below 40°F → winter + thick jacket
  - 40–65°F → fall/spring + light jacket
  - 66–75°F → fall/spring
  - above 75°F → summer, with shorts
- **Outfit builder + saved outfits**: pick items by hand, save, browse, edit, delete, and log when you wore an outfit (the wear log).
