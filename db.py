import sqlite3
import sys
from typing import Optional

import sqlite_vec

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
        print("Use Homebrew Python: source .venv/bin/activate", file=sys.stderr)
        sys.exit(1)
    except sqlite3.OperationalError as e:
        print(f"ERROR: Failed to load sqlite-vec extension: {e}", file=sys.stderr)
        print("Use Homebrew Python: source .venv/bin/activate", file=sys.stderr)
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


def db_search_text(conn: sqlite3.Connection, translation: str, query: str, limit: int):
    return conn.execute(
        """
        SELECT b.name AS book, b.osis_id, v.chapter, v.verse, v.text,
               verses_fts.rank AS score
        FROM verses_fts
        JOIN verses v ON v.id = verses_fts.rowid
        JOIN books b ON b.id = v.book_id
        JOIN translations t ON t.id = v.translation_id
        WHERE verses_fts MATCH ? AND t.abbreviation = ?
        ORDER BY verses_fts.rank
        LIMIT ?
        """,
        (query, translation, limit),
    ).fetchall()


def db_search_semantic(conn: sqlite3.Connection, query_text: str,
                       translation: str, limit: int):
    model = _get_model()
    embedding = model.encode(query_text, convert_to_numpy=True)
    blob = sqlite_vec.serialize_float32(embedding.tolist())
    k = limit * 4
    return conn.execute(
        """
        SELECT ve.verse_id, ve.distance, v.chapter, v.verse, v.text,
               b.name AS book, b.osis_id
        FROM verse_embeddings ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        JOIN translations t ON t.id = v.translation_id
        WHERE ve.embedding MATCH ? AND k = ?
          AND t.abbreviation = ?
        ORDER BY ve.distance
        LIMIT ?
        """,
        (blob, k, translation, limit),
    ).fetchall()


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
