"""CloSet50: a digital wardrobe where users catalog their clothes and put together outfits.

Run with:  flask run   (or: python app.py)
"""

import os
import sqlite3
import uuid

from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import (CATEGORIES, OCCASIONS, SEASONS, generate_outfit, get_temperature,
                     login_required, save_image, weather_rules)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-for-your-final-project")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB uploads max

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
DATABASE = os.path.join(app.root_path, "closet.db")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


# ---------- Database helpers ----------

def db_execute(query, *args):
    """Run a SQL query. SELECTs return a list of rows (dicts); INSERTs return the new id."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(query, args)
    if query.strip().upper().startswith("SELECT"):
        result = [dict(row) for row in cursor.fetchall()]
    else:
        connection.commit()
        result = cursor.lastrowid
    connection.close()
    return result


def setup():
    """Create the uploads folder and the database tables if they don't exist yet."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with open(os.path.join(app.root_path, "schema.sql")) as f:
        connection = sqlite3.connect(DATABASE)
        connection.executescript(f.read())
        connection.close()


setup()


@app.context_processor
def tag_lists():
    """Make the tag lists available in every template."""
    return {"CATEGORIES": CATEGORIES, "OCCASIONS": OCCASIONS, "SEASONS": SEASONS}


# ---------- Accounts ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip().lower()

        if not username or not password or not question or not answer:
            flash("Please fill in every field.")
        elif password != confirmation:
            flash("Passwords don't match.")
        elif db_execute("SELECT id FROM users WHERE username = ?", username):
            flash("That username is taken.")
        else:
            user_id = db_execute(
                "INSERT INTO users (username, hash, security_question, security_answer_hash) "
                "VALUES (?, ?, ?, ?)",
                username, generate_password_hash(password), question, generate_password_hash(answer))
            session["user_id"] = user_id
            session["username"] = username
            flash("Welcome to CloSet50! Start by uploading some clothes.")
            return redirect("/upload")
        return render_template("register.html")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        rows = db_execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password", "")):
            flash("Invalid username or password.")
            return render_template("login.html")
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """Reset a password by answering the security question chosen at sign up."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        rows = db_execute("SELECT * FROM users WHERE username = ?", username)
        if not rows:
            flash("No account with that username.")
            return render_template("reset.html")
        user = rows[0]

        # Step 1: they only typed a username, so show them their question
        if "answer" not in request.form:
            return render_template("reset.html", username=username, question=user["security_question"])

        # Step 2: check the answer and save the new password
        answer = request.form.get("answer", "").strip().lower()
        password = request.form.get("password", "")
        if not check_password_hash(user["security_answer_hash"], answer):
            flash("That answer doesn't match.")
        elif not password or password != request.form.get("confirmation"):
            flash("New passwords must match.")
        else:
            db_execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(password), user["id"])
            flash("Password reset! You can log in now.")
            return redirect("/login")
        return render_template("reset.html", username=username, question=user["security_question"])
    return render_template("reset.html")


# ---------- Closet view ----------

@app.route("/")
@login_required
def closet():
    """Show every item in a grid, with optional filters from the URL (?category=top&season=summer)."""
    category = request.args.get("category", "")
    occasion = request.args.get("occasion", "")
    season = request.args.get("season", "")

    items = db_execute("SELECT * FROM items WHERE user_id = ? ORDER BY category, name", session["user_id"])
    if category:
        items = [i for i in items if i["category"] == category]
    if occasion:
        items = [i for i in items if occasion in i["occasions"].split(",")]
    if season:
        items = [i for i in items if season in i["seasons"].split(",")]

    return render_template("closet.html", items=items, category=category, occasion=occasion, season=season)


def read_item_form():
    """Read the tag fields shared by the upload and edit forms. Returns (data, error)."""
    data = {
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category", ""),
        "subtype": request.form.get("subtype", ""),
        "color": request.form.get("color", "").strip().lower(),
        "occasions": ",".join(o for o in request.form.getlist("occasions") if o in OCCASIONS),
        "seasons": ",".join(s for s in request.form.getlist("seasons") if s in SEASONS),
    }
    if not data["name"]:
        return data, "Give the item a name."
    if data["category"] not in CATEGORIES:
        return data, "Choose a clothing type."
    if CATEGORIES[data["category"]] and data["subtype"] not in CATEGORIES[data["category"]]:
        return data, "Choose a style for this clothing type."
    if not CATEGORIES[data["category"]]:
        data["subtype"] = ""
    if not data["occasions"]:
        return data, "Choose at least one occasion."
    if not data["seasons"]:
        return data, "Choose at least one season."
    return data, None


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        data, error = read_item_form()
        photo = request.files.get("photo")
        if not photo or photo.filename == "":
            error = "Choose a photo to upload."
        elif photo.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_EXTENSIONS:
            error = "Photos must be .png or .jpg files."
        if error:
            flash(error)
            return render_template("item_form.html", item=data, editing=False)

        # Give the file a random unique name so two uploads never collide
        filename = uuid.uuid4().hex + ".png"
        try:
            save_image(photo, os.path.join(UPLOAD_FOLDER, filename), request.form.get("remove_bg") == "on")
        except Exception:
            flash("Sorry, that image couldn't be opened.")
            return render_template("item_form.html", item=data, editing=False)

        db_execute(
            "INSERT INTO items (user_id, name, category, subtype, color, occasions, seasons, image) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            session["user_id"], data["name"], data["category"], data["subtype"], data["color"],
            data["occasions"], data["seasons"], filename)
        flash(f"Added {data['name']} to your closet!")
        return redirect("/upload" if request.form.get("another") else "/")
    return render_template("item_form.html", item={}, editing=False)


def get_item(item_id):
    """Return one of the logged-in user's items, or None."""
    rows = db_execute("SELECT * FROM items WHERE id = ? AND user_id = ?", item_id, session["user_id"])
    return rows[0] if rows else None


@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = get_item(item_id)
    if not item:
        return redirect("/")
    if request.method == "POST":
        data, error = read_item_form()
        if error:
            flash(error)
            data["id"], data["image"] = item["id"], item["image"]
            return render_template("item_form.html", item=data, editing=True)
        db_execute(
            "UPDATE items SET name = ?, category = ?, subtype = ?, color = ?, occasions = ?, seasons = ? "
            "WHERE id = ?",
            data["name"], data["category"], data["subtype"], data["color"],
            data["occasions"], data["seasons"], item_id)
        flash("Item updated.")
        return redirect("/")
    return render_template("item_form.html", item=item, editing=True)


@app.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete(item_id):
    item = get_item(item_id)
    if item:
        db_execute("DELETE FROM outfit_items WHERE item_id = ?", item_id)
        db_execute("DELETE FROM items WHERE id = ?", item_id)
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, item["image"]))
        except OSError:
            pass
        flash(f"Removed {item['name']}.")
    return redirect("/")


# ---------- Outfit generator (filters, occasion, weather) ----------

@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "GET":
        return render_template("generate.html", form={})

    form = {
        "occasion": request.form.get("occasion", ""),
        "season": request.form.get("season", ""),
        "temp": request.form.get("temp", "").strip(),
        "city": request.form.get("city", "").strip(),
    }

    # Work out the temperature: typed in, or looked up from a city
    temp = None
    if form["temp"]:
        try:
            temp = int(float(form["temp"]))
        except ValueError:
            flash("Temperature must be a number.")
            return render_template("generate.html", form=form)
    elif form["city"]:
        temp = get_temperature(form["city"])
        if temp is None:
            flash(f"Couldn't get the weather for \"{form['city']}\". Try typing the temperature instead.")
            return render_template("generate.html", form=form)
        form["temp"] = str(temp)

    # Turn the temperature (or chosen season) into rules
    if temp is not None:
        seasons, jacket, shorts_only = weather_rules(temp)
    else:
        seasons = [form["season"]] if form["season"] else []
        jacket = "thick" if form["season"] == "winter" else None
        shorts_only = False

    items = db_execute("SELECT * FROM items WHERE user_id = ?", session["user_id"])
    outfit, missing = generate_outfit(items, form["occasion"], seasons, jacket, shorts_only)

    return render_template("generate.html", form=form, outfit=outfit, missing=missing,
                           temp=temp, seasons=seasons, jacket=jacket)


# ---------- Building and saving outfits ----------

@app.route("/build", methods=["GET", "POST"])
@login_required
def build():
    """Pick items by hand and save them as an outfit (or edit an existing outfit)."""
    outfit_id = request.values.get("outfit", type=int)
    outfit = None
    if outfit_id:
        rows = db_execute("SELECT * FROM outfits WHERE id = ? AND user_id = ?", outfit_id, session["user_id"])
        outfit = rows[0] if rows else None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        my_item_ids = {i["id"] for i in db_execute("SELECT id FROM items WHERE user_id = ?", session["user_id"])}
        item_ids = [int(i) for i in request.form.getlist("item_ids") if i.isdigit() and int(i) in my_item_ids]
        if not name or not item_ids:
            flash("Give your outfit a name and pick at least one item.")
            return redirect(request.referrer or "/build")

        if outfit:
            db_execute("UPDATE outfits SET name = ? WHERE id = ?", name, outfit["id"])
            db_execute("DELETE FROM outfit_items WHERE outfit_id = ?", outfit["id"])
            new_id = outfit["id"]
        else:
            new_id = db_execute("INSERT INTO outfits (user_id, name) VALUES (?, ?)", session["user_id"], name)
        for item_id in item_ids:
            db_execute("INSERT INTO outfit_items (outfit_id, item_id) VALUES (?, ?)", new_id, item_id)
        flash(f"Saved outfit \"{name}\".")
        return redirect("/outfits")

    items = db_execute("SELECT * FROM items WHERE user_id = ? ORDER BY category, name", session["user_id"])
    selected = []
    if outfit:
        selected = [r["item_id"] for r in db_execute(
            "SELECT item_id FROM outfit_items WHERE outfit_id = ?", outfit["id"])]
    return render_template("build.html", items=items, outfit=outfit, selected=selected)


@app.route("/outfits")
@login_required
def outfits():
    """Browse saved outfits."""
    saved = db_execute("SELECT * FROM outfits WHERE user_id = ? ORDER BY created DESC", session["user_id"])
    for outfit in saved:
        outfit["items"] = db_execute(
            "SELECT items.* FROM items JOIN outfit_items ON items.id = outfit_items.item_id "
            "WHERE outfit_items.outfit_id = ?", outfit["id"])
        worn = db_execute("SELECT COUNT(*) AS n, MAX(worn_on) AS last FROM wear_log WHERE outfit_id = ?",
                          outfit["id"])[0]
        outfit["times_worn"], outfit["last_worn"] = worn["n"], worn["last"]
    return render_template("outfits.html", outfits=saved)


@app.route("/outfits/<int:outfit_id>/delete", methods=["POST"])
@login_required
def delete_outfit(outfit_id):
    if db_execute("SELECT id FROM outfits WHERE id = ? AND user_id = ?", outfit_id, session["user_id"]):
        db_execute("DELETE FROM outfit_items WHERE outfit_id = ?", outfit_id)
        db_execute("DELETE FROM wear_log WHERE outfit_id = ?", outfit_id)
        db_execute("DELETE FROM outfits WHERE id = ?", outfit_id)
        flash("Outfit deleted.")
    return redirect("/outfits")


@app.route("/outfits/<int:outfit_id>/wear", methods=["POST"])
@login_required
def wear_outfit(outfit_id):
    """Add today to the wear log for this outfit."""
    if db_execute("SELECT id FROM outfits WHERE id = ? AND user_id = ?", outfit_id, session["user_id"]):
        db_execute("INSERT INTO wear_log (user_id, outfit_id) VALUES (?, ?)", session["user_id"], outfit_id)
        flash("Logged as worn today.")
    return redirect("/outfits")


if __name__ == "__main__":
    app.run(debug=True)
