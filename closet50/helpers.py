"""Helper functions for CloSet50 (login check, image processing, weather, outfit rules)."""

import json
import random
import urllib.parse
import urllib.request
from functools import wraps

from flask import redirect, session
from PIL import Image, ImageDraw


# ---------- The predetermined tags (from the project outline) ----------

CATEGORIES = {
    "top": ["long sleeves", "short sleeves", "tank top"],
    "bottom": ["shorts", "pants", "skirt"],
    "dress": [],
    "shoes": [],
    "outerwear": ["thick", "light"],
}
OCCASIONS = ["casual", "date", "formal", "athletic"]
SEASONS = ["spring", "summer", "fall", "winter"]


# ---------- Login ----------

def login_required(f):
    """Send the user to the login page if they are not logged in (same idea as Finance)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# ---------- Images ----------

def save_image(file, path, remove_bg):
    """Shrink the uploaded photo, optionally remove its background, and save it as a PNG."""
    img = Image.open(file).convert("RGBA")
    img.thumbnail((800, 800))  # keep files small

    if remove_bg:
        img = remove_background(img)

    img.save(path, "PNG")


def remove_background(img):
    """Remove the background of a clothing photo.

    If the 'rembg' library is installed (pip install rembg) we use it, because it uses
    a machine-learning model and works on any background. Otherwise we fall back to a
    simple method: starting from each corner, "paint bucket" fill everything that is
    close to the corner's color with transparent pixels. This works well when the
    clothes are photographed on a plain background (a bed, floor, or wall).
    """
    try:
        from rembg import remove
        return remove(img)
    except ImportError:
        pass

    width, height = img.size
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    for corner in corners:
        # Skip corners that an earlier fill already made transparent
        if img.getpixel(corner)[3] != 0:
            ImageDraw.floodfill(img, corner, (0, 0, 0, 0), thresh=45)
    return img


# ---------- Weather ----------

def get_temperature(city):
    """Return today's high temperature (°F) for a city using the free Open-Meteo API, or None."""
    try:
        # Step 1: turn the city name into latitude/longitude
        url = ("https://geocoding-api.open-meteo.com/v1/search?count=1&name="
               + urllib.parse.quote(city))
        with urllib.request.urlopen(url, timeout=10) as response:
            places = json.load(response).get("results")
        if not places:
            return None
        lat, lon = places[0]["latitude"], places[0]["longitude"]

        # Step 2: get today's forecast high
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               "&daily=temperature_2m_max&temperature_unit=fahrenheit&timezone=auto&forecast_days=1")
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
        return round(data["daily"]["temperature_2m_max"][0])
    except Exception:
        return None


def weather_rules(temp):
    """Turn a temperature into outfit rules (from the outline's Daily Weather Function).

    Returns (seasons to look for, jacket type needed or None, bottoms must be shorts?)
    """
    if temp < 40:
        return ["winter"], "thick", False
    elif temp <= 65:
        return ["fall", "spring"], "light", False
    elif temp <= 75:
        return ["fall", "spring"], None, False
    else:
        return ["summer"], None, True


# ---------- Outfit generator ----------

def matches(item, occasion, seasons):
    """True if an item has the chosen occasion and at least one of the chosen seasons."""
    item_occasions = item["occasions"].split(",")
    item_seasons = item["seasons"].split(",")
    if occasion and occasion not in item_occasions:
        return False
    if seasons and not any(s in item_seasons for s in seasons):
        return False
    return True


def generate_outfit(items, occasion, seasons, jacket, shorts_only):
    """Randomly build an outfit from a list of items.

    Rules (from the outline): one top + one bottom + shoes, OR a dress + shoes,
    plus a jacket when it's cold. Returns (list of chosen items, list of missing things).
    """
    # Group the matching items by category
    groups = {category: [] for category in CATEGORIES}
    for item in items:
        if matches(item, occasion, seasons):
            groups[item["category"]].append(item)

    tops = groups["top"]
    bottoms = groups["bottom"]
    if shorts_only:
        bottoms = [b for b in bottoms if b["subtype"] == "shorts"]
    dresses = groups["dress"]
    shoes = groups["shoes"]
    jackets = [j for j in groups["outerwear"] if j["subtype"] == jacket]

    # Figure out which outfit "shapes" are possible
    options = []
    if tops and bottoms:
        options.append("separates")
    if dresses:
        options.append("dress")

    # Error handling: list everything that's missing
    missing = []
    if not options:
        if not tops:
            missing.append("a top")
        if not bottoms:
            missing.append("shorts" if shorts_only else "a bottom")
        missing[-1] += " (or a dress)"
    if not shoes:
        missing.append("shoes")
    if jacket and not jackets:
        missing.append(f"a {jacket} jacket")
    if missing:
        return [], missing

    # Randomly choose the outfit
    outfit = []
    if random.choice(options) == "separates":
        outfit.append(random.choice(tops))
        outfit.append(random.choice(bottoms))
    else:
        outfit.append(random.choice(dresses))
    outfit.append(random.choice(shoes))
    if jacket:
        outfit.append(random.choice(jackets))
    return outfit, []
