-- CloSet50 database schema
-- Create the database with:  sqlite3 closet.db < schema.sql
-- (app.py also runs this automatically the first time it starts)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    security_question TEXT NOT NULL,
    security_answer_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,      -- top, bottom, dress, shoes, outerwear
    subtype TEXT,                -- e.g. long sleeves, shorts, thick, light
    color TEXT,
    occasions TEXT NOT NULL,     -- comma separated, e.g. "casual,date"
    seasons TEXT NOT NULL,       -- comma separated, e.g. "fall,winter"
    image TEXT NOT NULL,         -- file name inside static/uploads
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS outfits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS outfit_items (
    outfit_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    FOREIGN KEY (outfit_id) REFERENCES outfits(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS wear_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    outfit_id INTEGER NOT NULL,
    worn_on DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (outfit_id) REFERENCES outfits(id)
);
