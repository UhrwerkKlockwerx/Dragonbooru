"""SQLite data access for the application.

This module intentionally knows nothing about Qt or any other UI toolkit. UI
code should call the public functions at the bottom of this file (or use a
``Database`` instance) and receive ordinary Python values back.

The default database lives beside the application entry point as
``database.db``. Pass an explicit path in tests or when another data directory
is intentionally selected.

The modularity and fascia approach allows much easier modification to the
elements that require database access.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SUPPORTED_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".avif",
    ".heic", ".jp2", ".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv",
    ".wmv", ".m4v",
})


class DatabaseError(RuntimeError):
    """Raised when a database operation cannot be completed safely."""


@dataclass(frozen=True)
class ScanResult:
    """Summary returned by :meth:`Database.scan_folders`."""

    folders_seen: int
    files_seen: int
    supported_files: int
    inserted: int
    skipped_missing_folders: tuple[str, ...]


def default_database_path() -> Path:
    """Return the database path in the application's primary folder."""

    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return root / "database.db"


def _canonical_path(path: str | os.PathLike[str]) -> str:
    """Normalize a media path without requiring it to exist."""

    return os.path.normcase(os.path.abspath(os.fspath(path)))


class Database:
    """Connection-owning repository for images, tags, and pools."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.row_factory = sqlite3.Row
            self._create_schema()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not open database {self.path}: {exc}") from exc

    def _create_schema(self) -> None:
        """Create the current schema and its indexes if they do not exist."""

        try:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    modified_at REAL,
                    file_size INTEGER
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                );

                CREATE TABLE IF NOT EXISTS image_tags (
                    image_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (image_id, tag_id),
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS pools (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    description TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS pool_items (
                    pool_id INTEGER NOT NULL,
                    image_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (pool_id, image_id),
                    UNIQUE (pool_id, position),
                    FOREIGN KEY (pool_id) REFERENCES pools(id) ON DELETE CASCADE,
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_images_path ON images(path);
                CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
                CREATE INDEX IF NOT EXISTS idx_image_tags_tag ON image_tags(tag_id);
                CREATE INDEX IF NOT EXISTS idx_pool_items_image ON pool_items(image_id);
                """
            )
            current = self.connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'version'"
            ).fetchone()
            if current is None:
                self.connection.execute(
                    "INSERT INTO schema_meta(key, value) VALUES('version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(current[0]) > self.SCHEMA_VERSION:
                raise DatabaseError(
                    "The database was created by a newer application version."
                )
            self.connection.commit()
        except (sqlite3.Error, ValueError) as exc:
            self.connection.rollback()
            raise DatabaseError(f"Could not initialize database schema: {exc}") from exc

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.close()

    # ----- image indexing -------------------------------------------------

    def scan_folders(self, folders: Iterable[str | os.PathLike[str]]) -> ScanResult:
        """Index supported files beneath *folders* without touching media.

        This method is deliberately synchronous and UI-independent. A future
        Qt worker can call it in a background thread and relay ``ScanResult``
        when it completes.
        """

        folder_list = [Path(folder).expanduser() for folder in folders]
        missing: list[str] = []
        files_seen = supported = inserted = 0

        try:
            with self.connection:
                for folder in folder_list:
                    if not folder.is_dir():
                        missing.append(str(folder))
                        continue
                    for root, _dirs, files in os.walk(folder):
                        for filename in files:
                            files_seen += 1
                            path = Path(root) / filename
                            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                                continue
                            supported += 1
                            canonical = _canonical_path(path)
                            stat = path.stat()
                            cursor = self.connection.execute(
                                """
                                INSERT OR IGNORE INTO images(path, modified_at, file_size)
                                VALUES (?, ?, ?)
                                """,
                                (canonical, stat.st_mtime, stat.st_size),
                            )
                            inserted += cursor.rowcount
        except (OSError, sqlite3.Error) as exc:
            raise DatabaseError(f"Could not scan media folders: {exc}") from exc

        return ScanResult(
            folders_seen=len(folder_list),
            files_seen=files_seen,
            supported_files=supported,
            inserted=inserted,
            skipped_missing_folders=tuple(missing),
        )

    def list_images(self, limit: int | None = None, offset: int = 0) -> list[str]:
        query = "SELECT path FROM images ORDER BY path"
        params: list[int] = []
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend((max(0, limit), max(0, offset)))
        return [row[0] for row in self.connection.execute(query, params)]

    def get_image_id(self, path: str | os.PathLike[str]) -> int | None:
        row = self.connection.execute(
            "SELECT id FROM images WHERE path = ?", (_canonical_path(path),)
        ).fetchone()
        return int(row[0]) if row else None

    def delete_image_record(self, path: str | os.PathLike[str]) -> bool:
        """Remove only the database record; the caller must handle the file."""

        cursor = self.connection.execute(
            "DELETE FROM images WHERE path = ?", (_canonical_path(path),)
        )
        self.connection.commit()
        return cursor.rowcount > 0

    # ----- tags and search ------------------------------------------------

    def get_tags(self, path: str | os.PathLike[str]) -> list[str]:
        image_id = self.get_image_id(path)
        if image_id is None:
            return []
        rows = self.connection.execute(
            """
            SELECT tags.name FROM tags
            JOIN image_tags ON image_tags.tag_id = tags.id
            WHERE image_tags.image_id = ? ORDER BY tags.name COLLATE NOCASE
            """,
            (image_id,),
        )
        return [row[0] for row in rows]

    def add_tag(self, path: str | os.PathLike[str], tag: str) -> bool:
        cleaned = tag.strip()
        image_id = self.get_image_id(path)
        if not cleaned or image_id is None:
            return False
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO tags(name) VALUES(?)", (cleaned,)
            )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO image_tags(image_id, tag_id)
                SELECT ?, id FROM tags WHERE name = ?
                """,
                (image_id, cleaned),
            )
        return True

    def remove_tag(self, path: str | os.PathLike[str], tag: str) -> bool:
        image_id = self.get_image_id(path)
        if image_id is None:
            return False
        cursor = self.connection.execute(
            """
            DELETE FROM image_tags
            WHERE image_id = ? AND tag_id = (SELECT id FROM tags WHERE name = ?)
            """,
            (image_id, tag.strip()),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def autocomplete_tags(self, prefix: str, limit: int = 15) -> list[tuple[str, int]]:
        """Return matching tags and usage counts for a future Qt completer."""

        query = f"%{prefix.strip()}%"
        rows = self.connection.execute(
            """
            SELECT tags.name, COUNT(image_tags.image_id) AS usage
            FROM tags LEFT JOIN image_tags ON image_tags.tag_id = tags.id
            WHERE tags.name LIKE ? COLLATE NOCASE
            GROUP BY tags.id
            ORDER BY usage DESC, tags.name COLLATE NOCASE
            LIMIT ?
            """,
            (query, max(1, limit)),
        )
        return [(row[0], int(row[1])) for row in rows]

    @staticmethod
    def parse_search_query(query: str) -> tuple[list[str], list[str]]:
        required: list[str] = []
        excluded: list[str] = []
        for part in query.split(","):
            tag = part.strip()
            if not tag:
                continue
            (excluded if tag.startswith("-") else required).append(
                tag[1:].strip() if tag.startswith("-") else tag
            )
        return required, excluded

    def search_images(
        self,
        required: Sequence[str] | str = (),
        excluded: Sequence[str] = (),
    ) -> list[str]:
        if isinstance(required, str):
            required, parsed_excluded = self.parse_search_query(required)
            excluded = list(excluded) + parsed_excluded

        joins: list[str] = []
        conditions: list[str] = []
        params: list[str] = []
        for index, tag in enumerate(required):
            joins.extend((
                f"JOIN image_tags req_links_{index} ON req_links_{index}.image_id = images.id",
                f"JOIN tags req_tags_{index} ON req_tags_{index}.id = req_links_{index}.tag_id AND req_tags_{index}.name = ?",
            ))
            params.append(tag.strip())
        for tag in excluded:
            conditions.append(
                "images.id NOT IN (SELECT image_id FROM image_tags "
                "JOIN tags ON tags.id = image_tags.tag_id WHERE tags.name = ?)"
            )
            params.append(tag.strip())

        sql = "SELECT DISTINCT images.path FROM images " + " ".join(joins)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY images.path"
        return [row[0] for row in self.connection.execute(sql, params)]

    # ----- pools ----------------------------------------------------------

    def create_pool(self, name: str, description: str = "") -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("A pool name cannot be empty.")
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "INSERT INTO pools(name, description) VALUES(?, ?)",
                    (cleaned, description.strip()),
                )
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"A pool named {cleaned!r} already exists.") from exc

    def list_pools(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            """
            SELECT pools.id, pools.name, pools.description,
                   COUNT(pool_items.image_id) AS item_count
            FROM pools LEFT JOIN pool_items ON pool_items.pool_id = pools.id
            GROUP BY pools.id ORDER BY pools.name COLLATE NOCASE
            """
        ))

    def add_to_pool(self, pool_id: int, image_id: int, position: int | None = None) -> None:
        if position is None:
            row = self.connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM pool_items WHERE pool_id = ?",
                (pool_id,),
            ).fetchone()
            position = int(row[0])
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO pool_items(pool_id, image_id, position) VALUES(?, ?, ?)",
                (pool_id, image_id, position),
            )

    def get_pool_images(self, pool_id: int) -> list[str]:
        rows = self.connection.execute(
            """
            SELECT images.path FROM pool_items
            JOIN images ON images.id = pool_items.image_id
            WHERE pool_items.pool_id = ? ORDER BY pool_items.position
            """,
            (pool_id,),
        )
        return [row[0] for row in rows]


# Lazy module-level facade: UI code can call ``db.search_images(...)`` without
# opening a connection merely by importing this module.
_default_database: Database | None = None


def get_database(path: str | os.PathLike[str] | None = None) -> Database:
    global _default_database
    if _default_database is None:
        _default_database = Database(path)
    return _default_database


def close_database() -> None:
    global _default_database
    if _default_database is not None:
        _default_database.close()
        _default_database = None


def scan_folders(folders: Iterable[str | os.PathLike[str]]) -> ScanResult:
    return get_database().scan_folders(folders)


def list_images(limit: int | None = None, offset: int = 0) -> list[str]:
    return get_database().list_images(limit, offset)


def get_tags(path: str | os.PathLike[str]) -> list[str]:
    return get_database().get_tags(path)


def add_tag(path: str | os.PathLike[str], tag: str) -> bool:
    return get_database().add_tag(path, tag)


def remove_tag(path: str | os.PathLike[str], tag: str) -> bool:
    return get_database().remove_tag(path, tag)


def autocomplete_tags(prefix: str, limit: int = 15) -> list[tuple[str, int]]:
    return get_database().autocomplete_tags(prefix, limit)


def search_images(required: Sequence[str] | str = (), excluded: Sequence[str] = ()) -> list[str]:
    return get_database().search_images(required, excluded)


def create_pool(name: str, description: str = "") -> int:
    return get_database().create_pool(name, description)


def list_pools() -> list[sqlite3.Row]:
    return get_database().list_pools()


def get_pool_images(pool_id: int) -> list[str]:
    return get_database().get_pool_images(pool_id)
