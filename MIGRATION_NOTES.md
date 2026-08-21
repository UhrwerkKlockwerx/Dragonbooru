# Legacy BUILD migration notes

This document records features attempted in `/home/kmordim/Desktop/BUILD` after
the last committed Drakindex legacy build. It is a planning reference for the Qt
rewrite, not source code to copy directly.

## Decision rule

First complete a navigable Qt shell (menu, search, settings, viewer, and
What's New). Then port each feature through a dedicated service and test it in
isolation. Do not move the legacy `main.py` logic wholesale into a Qt window.

## Features worth carrying forward

| Feature | Legacy approach | Qt rewrite direction | Priority |
| --- | --- | --- | --- |
| Configurable scan folders | `settings["scan_folders"]`; settings list with Add/Remove | Settings page with a list, folder picker, validation, and explicit rescan action | High |
| Index multiple folders | Walk every configured folder and add supported media to SQLite | `LibraryScanner` service; preserve paths exactly and report missing/unreadable folders | High |
| Stable thumbnail paths | Encodes absolute source path (including drive) beneath thumbnail root | Use a stable hash of the canonical path; avoid collisions and `..` paths | High |
| Usage-ranked autocomplete | SQL returns `(tag_name, usage)` and UI fuzzy-sorts candidates | `TagRepository.autocomplete()` returns a small typed result; Qt completer/model later | High |
| Pool browser | The legacy comic shelf establishes the interaction pattern | Pools group related media, including comics, through a dedicated repository and browser page | Medium |
| Viewer fit mode | Toggle between fit-to-window and width-only scrolling | Viewer setting; preserve aspect ratio and retain zoom/scroll state per item | Medium |
| Keyboard browsing | Previous/next controls and arrow-key navigation | Bind shortcuts only while the viewer page is active | Medium |
| Sequential tag workflow | Save & Previous / Save & Next, focused tag input | Tag editor page actions; ensure pending typed tags are saved before navigation | Medium |
| Add parent-folder tag | Normalizes immediate parent directory into a tag | Optional, previewable command with an exclusion list and undo/confirmation | Medium |
| Tag library | Categorized tag browser, usage/alphabetical sort, click to add | Searchable dialog/dock backed by a paginated model | Medium |
| Global tag manager | Find and remove tags; remove unused tags | Administrative tool with counts, confirmation, transaction, and backup | Medium |
| Theme additions | `bg_secondary` token and Fox Mode palette | Extend Qt theme schema only if the new UI needs a secondary surface token | Low |
| Portable Windows tools | Bundled `ffmpeg.exe` and `ffplay.exe` | Decide packaging policy separately; validate executable availability and keep platform fallbacks | Low |

## Feature details and migration safeguards

### Multiple scan folders and portable libraries

The abandoned build changes the library from a single managed image directory
to user-selected folders, initially defaulting to `~/Pictures`. This is the
most valuable functional change and should be implemented after the Settings
page exists.

- Persist a list of selected folders in user settings.
- Validate each path before saving and show inaccessible or missing folders.
- Scan in a worker thread; filesystem walks can block the GUI for a long time.
- Store canonical absolute paths and do not copy the user's media by default.
- On rescan, mark or report files that disappeared instead of leaving stale
  database records indefinitely.
- Keep the database, settings, cache, and thumbnails in a user-writable app
  data directory—not the application install directory or a drive root.

### Thumbnail cache

The abandoned `thumbnail_path()` tries to avoid `../` paths when media lies
outside one fixed library root. That goal is correct. The rewrite should use a
hash such as SHA-256 of the canonical source path plus a source modification
time in the cache key. This supports multiple drives and avoids collisions
between similarly named files.

### Autocomplete

The revised database query correctly returns a tag's usage count and searches
for the term anywhere in the name. This is intended to work with the revised
fuzzy-scoring entry widget.

Port the query and UI behavior together. The old committed repository returns
name strings only, while the abandoned autocomplete widget expects `(name,
count)` pairs. Mixing those two versions will crash or behave incorrectly.

### Pools

The prototype creates a comic shelf by interpreting `comic:name` tags, using
the first ordered image as cover art, and displaying page counts. Pools replace
that feature in the rewrite: a pool is a named, ordered group of related media
and can represent a comic, a set, or any other collection.

Pools need their own database tables rather than tags: `pools`, `pool_items`,
and an explicit position field. Make page/item ordering a first-class property;
alphabetical file order is not always the intended reading order. A pool browser
can reuse the shelf/grid visual idea without hiding its items from normal search.

### Viewer and rapid tag editing

The prototype adds fit-to-window mode, viewer previous/next navigation, tag
editor previous/next navigation, a parent-folder tag shortcut, and a tag
library/manager.

Port these only after the viewer and tag editor pages navigate correctly. Save
pending tag-entry text before moving to another item. Scope arrow and spacebar
shortcuts to the active page so that typing into other controls is unaffected.

### Tag administration

The tag library grouping and usage counts are useful. Suggested category
prefixes need a deliberate taxonomy; the prototype mixes `artist:`, `comic:`,
`character_`, and `species_`.

All global deletion actions require a transaction and a confirmation dialog.
The legacy delete implementation is unsafe: it deletes the `tags` row before
looking up its ID to delete `image_tags`, leaving orphan association rows.
Use foreign keys with `ON DELETE CASCADE`, or delete associations first inside
one transaction. Offer a database backup before bulk cleanup.

## Do not port unchanged

- The legacy `db.search_images()` is accidentally truncated: the new comic
  functions were inserted before its query-building body, so ordinary search
  returns `None`.
- `SearchPage` contains duplicate `apply_per_page`, `next_page`, and
  `set_current_comic` methods. The later definitions override earlier ones.
- The settings code catches every exception, logs debug paths at import time,
  and uses a Windows drive-root application directory. Replace it with clear
  errors and Qt's standard application-data location.
- Scanning runs on the GUI thread and has no missing-folder/error reporting.
- Global bindings and the spacebar shortcut can trigger navigation while a user
  is typing, potentially losing unsaved tag text.
- The large bundled FFmpeg binaries should not enter the new source tree until
  a packaging strategy is chosen.

## Implementation order after navigation is complete

1. Settings service and Settings page: theme, page size, safe mode, blacklist,
   then scan-folder list.
2. SQLite repository with migrations, foreign keys enabled, and a small test
   database.
3. Library scanner worker and thumbnail-cache service.
4. Search page result model, pagination, and clickable thumbnail grid.
5. Media viewer: image/GIF/video preview, fit mode, and next/previous actions.
6. Tag editor: add/remove tags, autocomplete, batch add, then rapid navigation.
7. Optional pool browser and tag-library/administration tools.

## Source inventory

The abandoned prototype consists of a 1,700-line Tkinter `main.py`, revised
`db.py`, `settings.py`, `theme.py`, and `autocomplete_entry.py`, plus bundled
`ffmpeg.exe`/`ffplay.exe`. Its changelog explicitly calls out folder scanning,
portable/external-drive use, tag sorting, and Fox Mode as the headline changes.
