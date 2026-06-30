import sqlite3
import sys
from typing import Optional

import sqlite_vec

from books import resolve_book

_conn: Optional[sqlite3.Connection] = None
_model = None


def get_connection(db_path: str) -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except AttributeError:
        print("ERROR: sqlite-vec requires a Python build with extension loading support.", file=sys.stderr)
        print("Ensure you are using the project virtualenv: source .venv/bin/activate", file=sys.stderr)
        sys.exit(1)
    except sqlite3.OperationalError as e:
        print(f"ERROR: Failed to load sqlite-vec extension: {e}", file=sys.stderr)
        print("Ensure you are using the project virtualenv: source .venv/bin/activate", file=sys.stderr)
        sys.exit(1)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_cached_connection(db_path: str) -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = get_connection(db_path)
    return _conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS translations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            abbreviation TEXT UNIQUE NOT NULL,
            name         TEXT NOT NULL,
            language     TEXT NOT NULL DEFAULT 'en',
            license      TEXT
        );

        CREATE TABLE IF NOT EXISTS books (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            translation_id INTEGER NOT NULL REFERENCES translations(id),
            osis_id        TEXT NOT NULL,
            name           TEXT NOT NULL,
            testament      TEXT NOT NULL CHECK(testament IN ('OT', 'NT')),
            book_order     INTEGER NOT NULL,
            UNIQUE(translation_id, osis_id)
        );

        CREATE TABLE IF NOT EXISTS verses (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            translation_id INTEGER NOT NULL REFERENCES translations(id),
            book_id        INTEGER NOT NULL REFERENCES books(id),
            chapter        INTEGER NOT NULL,
            verse          INTEGER NOT NULL,
            text           TEXT NOT NULL,
            UNIQUE(translation_id, book_id, chapter, verse)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(
            text,
            content=verses,
            content_rowid=id
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS verse_embeddings USING vec0(
            verse_id  INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        );

        CREATE TABLE IF NOT EXISTS cross_references (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_book       TEXT NOT NULL,
            from_chapter    INTEGER NOT NULL,
            from_verse      INTEGER NOT NULL,
            to_book         TEXT NOT NULL,
            to_chapter      INTEGER NOT NULL,
            to_verse_start  INTEGER NOT NULL,
            to_verse_end    INTEGER NOT NULL,
            votes           INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_cross_refs_from
        ON cross_references(from_book, from_chapter, from_verse);
    """)
    conn.commit()


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def db_get_verse(conn: sqlite3.Connection, translation: str, osis_id: str,
                 chapter: int, verse: int):
    osis_id = resolve_book(osis_id)
    if osis_id is None:
        return None
    return conn.execute(
        """
        SELECT t.abbreviation AS translation, b.name AS book, b.osis_id,
               v.chapter, v.verse, v.text
        FROM verses v
        JOIN books b ON b.id = v.book_id
        JOIN translations t ON t.id = v.translation_id
        WHERE t.abbreviation = ? AND b.osis_id = ? AND v.chapter = ? AND v.verse = ?
        """,
        (translation, osis_id, chapter, verse),
    ).fetchone()


def db_get_passage(conn: sqlite3.Connection, translation: str, osis_id: str,
                   chapter: int, verse_start: int, verse_end: int):
    osis_id = resolve_book(osis_id)
    if osis_id is None:
        return []
    return conn.execute(
        """
        SELECT v.verse, v.text
        FROM verses v
        JOIN books b ON b.id = v.book_id
        JOIN translations t ON t.id = v.translation_id
        WHERE t.abbreviation = ? AND b.osis_id = ? AND v.chapter = ?
          AND v.verse BETWEEN ? AND ?
        ORDER BY v.verse
        """,
        (translation, osis_id, chapter, verse_start, verse_end),
    ).fetchall()


_TESTAMENT_MAP = {
    "ot": "OT", "old": "OT", "old testament": "OT",
    "nt": "NT", "new": "NT", "new testament": "NT",
}


def resolve_testament(testament: Optional[str]) -> Optional[str]:
    """Normalize a testament string to 'OT' or 'NT', or None if not provided."""
    if testament is None:
        return None
    resolved = _TESTAMENT_MAP.get(testament.strip().lower())
    return resolved  # None means unrecognized — callers should treat as invalid


def db_search_text(conn: sqlite3.Connection, translation: str, query: str,
                   limit: int, testament: Optional[str] = None):
    t_filter = f"AND b.testament = '{testament}'" if testament else ""
    return conn.execute(
        f"""
        SELECT b.name AS book, b.osis_id, v.chapter, v.verse, v.text,
               verses_fts.rank AS score
        FROM verses_fts
        JOIN verses v ON v.id = verses_fts.rowid
        JOIN books b ON b.id = v.book_id
        JOIN translations t ON t.id = v.translation_id
        WHERE verses_fts MATCH ? AND t.abbreviation = ?
          {t_filter}
        ORDER BY verses_fts.rank
        LIMIT ?
        """,
        (query, translation, limit),
    ).fetchall()


def db_search_semantic(conn: sqlite3.Connection, query_text: str,
                       translation: str, limit: int,
                       testament: Optional[str] = None):
    model = _get_model()
    embedding = model.encode(query_text, convert_to_numpy=True)
    blob = sqlite_vec.serialize_float32(embedding.tolist())

    if testament:
        rowid_filter = """
            SELECT v2.id FROM verses v2
            JOIN books b2 ON b2.id = v2.book_id
            JOIN translations t2 ON t2.id = v2.translation_id
            WHERE t2.abbreviation = ? AND b2.testament = ?"""
        params = (translation, testament, blob, limit, limit)
    else:
        rowid_filter = """
            SELECT v2.id FROM verses v2
            JOIN translations t2 ON t2.id = v2.translation_id
            WHERE t2.abbreviation = ?"""
        params = (translation, blob, limit, limit)

    return conn.execute(
        f"""
        SELECT ve.verse_id, ve.distance, v.chapter, v.verse, v.text,
               b.name AS book, b.osis_id
        FROM verse_embeddings ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE ve.verse_id IN ({rowid_filter})
          AND ve.embedding MATCH ? AND k = ?
        ORDER BY ve.distance
        LIMIT ?
        """,
        params,
    ).fetchall()


def db_get_cross_references(conn: sqlite3.Connection, translation: str,
                            osis_id: str, chapter: int, verse: int,
                            min_votes: Optional[int], limit: int,
                            testament: Optional[str] = None):
    params: list = [osis_id, chapter, verse]
    votes_filter = ""
    if min_votes is not None:
        votes_filter = "AND cr.votes >= ?"
        params.append(min_votes)
    testament_filter = ""
    if testament:
        testament_filter = "AND cr.to_book IN (SELECT DISTINCT osis_id FROM books WHERE testament = ?)"
        params.append(testament)
    params.append(limit)

    refs = conn.execute(
        f"""
        SELECT cr.to_book, cr.to_chapter, cr.to_verse_start, cr.to_verse_end, cr.votes
        FROM cross_references cr
        WHERE cr.from_book = ? AND cr.from_chapter = ? AND cr.from_verse = ?
          {votes_filter}
          {testament_filter}
        ORDER BY cr.votes DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    results = []
    for ref in refs:
        to_book, to_chapter, to_verse_start, to_verse_end, votes = ref
        rows = db_get_passage(conn, translation, to_book, to_chapter, to_verse_start, to_verse_end)
        entry: dict = {
            "osis_id": to_book,
            "chapter": to_chapter,
            "verse_start": to_verse_start,
            "verse_end": to_verse_end,
            "votes": votes,
        }
        if rows:
            entry["verses"] = [{"verse": r["verse"], "text": r["text"]} for r in rows]
        results.append(entry)
    return results


def db_list_translations(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT id, abbreviation, name, language, license FROM translations ORDER BY id"
    ).fetchall()


def db_list_books(conn: sqlite3.Connection, translation: str):
    return conn.execute(
        """
        SELECT b.osis_id, b.name, b.testament, b.book_order
        FROM books b
        JOIN translations t ON t.id = b.translation_id
        WHERE t.abbreviation = ?
        ORDER BY b.book_order
        """,
        (translation,),
    ).fetchall()
