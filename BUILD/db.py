import os
from settings import *
import sqlite3

# Extraordinarily handy script to refresh the paths in the database to make sure
# all of the images read correctly in case the directories moved. E.g. an older
# dev build from before the home directory paths.
def refresh_image_paths():
    cur.execute("SELECT id, path FROM images")
    rows = cur.fetchall()
    updated = 0
    for img_id, old_path in rows:
        filename = os.path.basename(old_path)
        new_path = os.path.join(IMAGE_ROOT, filename)
        if old_path != new_path:
            cur.execute("UPDATE images SET path=? WHERE id=?", (new_path, img_id))
            updated += 1
    conn.commit()
    print(f"Refreshed paths for {updated} images.")

# The logic to make the autocomplete talk to the database. Fairly
# simple.
def autocomplete_tags(prefix, limit=15):
    cur.execute(
        "SELECT name FROM tags WHERE name LIKE ? LIMIT ?",
        (prefix + "%", limit)
    )
    return [r[0] for r in cur.fetchall()]

def get_image_id(path):
    cur.execute("SELECT id FROM images WHERE path=?", (path,))
    r = cur.fetchone()
    return r[0] if r else None

def get_tags_for_image_path(path):
    image_id = get_image_id(path)
    if not image_id:
        return []
    cur.execute("""
    SELECT tags.name FROM tags
    JOIN image_tags ON tags.id = image_tags.tag_id
    WHERE image_tags.image_id=?
    """, (image_id,))
    return [r[0] for r in cur.fetchall()]

def add_tag_to_image(path, tag):
    cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (tag,))
    cur.execute("SELECT id FROM tags WHERE name=?", (tag,))
    r = cur.fetchone()
    if not r:
        return
    tag_id = r[0]
    image_id = get_image_id(path)
    if image_id:
        cur.execute("INSERT OR IGNORE INTO image_tags VALUES(?,?)", (image_id, tag_id))
        conn.commit()

def remove_tag_from_image(path, tag):
    cur.execute("SELECT id FROM tags WHERE name=?", (tag,))
    r = cur.fetchone()
    if not r:
        return
    tag_id = r[0]
    image_id = get_image_id(path)
    if image_id:
        cur.execute("DELETE FROM image_tags WHERE image_id=? AND tag_id=?", (image_id, tag_id))
        conn.commit()

def search_images(required, excluded):
    # returns list of image paths matching the query
    sql = "SELECT images.path FROM images "
    joins = []
    conditions = []
    params = []

    # for each required tag we JOIN to ensure presence
    for i, tag in enumerate(required):
        joins.append(f"JOIN image_tags it_req{i} ON images.id = it_req{i}.image_id")
        joins.append(f"JOIN tags t_req{i} ON it_req{i}.tag_id = t_req{i}.id AND t_req{i}.name = ?")
        params.append(tag)

    # for excluded tags we add a NOT IN condition
    for tag in excluded:
        conditions.append("""
            images.id NOT IN (
                SELECT image_id FROM image_tags
                JOIN tags ON tags.id=image_tags.tag_id
                WHERE tags.name = ?
            )
        """)
        params.append(tag)

    sql += " " + " ".join(joins)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    cur.execute(sql, params)
    return [r[0] for r in cur.fetchall()]

def parse_search_query(qtext):
    # Accept comma-separated tags (strip whitespace). Example: "spyro, -cynder, artist:elicitie"
    parts = [p.strip() for p in qtext.split(",") if p.strip() != ""]
    required = []
    excluded = []
    for p in parts:
        if p.startswith("-"):
            excluded.append(p[1:].strip())
        else:
            required.append(p)
    return required, excluded

# scan image folder and insert missing images into DB
def scan_and_index_images():
    inserted = 0
    for root, dirs, files in os.walk(IMAGE_ROOT):
        for f in files:
            if f.lower().endswith(SUPPORTED_EXT):
                p = os.path.join(root, f)
                cur.execute("INSERT OR IGNORE INTO images(path) VALUES(?)", (p,))
                if cur.rowcount == 1:
                    inserted += 1
    conn.commit()
    return inserted


def process_deletions():
    if os.path.exists(delcache):
        with open(delcache, 'r') as f:
            for path in f.read().splitlines():
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        print('Deleted image: ', path)
                    thumb = thumbnail_path(path)
                    if os.path.exists(thumb):
                        os.remove(thumb)
                        print('Deleted thumbnail: ', thumb)
                    # Delete from db too...
                    cur.execute("DELETE FROM images WHERE path=?", (path,))
                    cur.execute("DELETE FROM image_tags WHERE image_id NOT IN (SELECT id FROM images)")
                except Exception as e:
                    print('Failed to delete "', path, '." ', e)
            conn.commit()
            os.remove(delcache) # Clean up the cache file.

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS images(
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS tags(
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS image_tags(
    image_id INTEGER,
    tag_id INTEGER,
    UNIQUE(image_id, tag_id)
)
""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_image_tags_image ON image_tags(image_id);
""")
cur.execute("""CREATE INDEX IF NOT EXISTS idx_image_tags_tag ON image_tags(tag_id);""")

