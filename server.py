import os
import sys
from contextlib import asynccontextmanager

from fastmcp import FastMCP

import db

DB_PATH = os.environ.get("BIBLE_DB_PATH", "bible.db")


@asynccontextmanager
async def lifespan(server: FastMCP):
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        print("Run: python scripts/ingest.py --file data/web.xml --translation web --name 'World English Bible'", file=sys.stderr)
        sys.exit(1)
    try:
        conn = db.get_connection(DB_PATH)
        conn.execute("SELECT vec_version()")
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: sqlite-vec startup check failed: {e}", file=sys.stderr)
        print("Ensure you are using Homebrew Python: source .venv/bin/activate", file=sys.stderr)
        sys.exit(1)
    yield {}


mcp = FastMCP("Bible", lifespan=lifespan)


@mcp.tool
def get_verse(translation: str, book: str, chapter: int, verse: int) -> dict:
    """Look up a specific Bible verse by reference. 'book' accepts full names,
    common abbreviations, or OSIS IDs — e.g. 'Genesis', 'Gen', 'ge', 'First Samuel',
    'Song of Songs', 'Rev' all work. Case-insensitive."""
    conn = db.get_cached_connection(DB_PATH)
    result = db.db_get_verse(conn, translation, book, chapter, verse)
    if result is None:
        return {"error": f"Verse not found: {translation} {book} {chapter}:{verse}"}
    return dict(result)


@mcp.tool
def get_passage(translation: str, book: str, chapter: int,
                verse_start: int, verse_end: int) -> dict:
    """Retrieve a range of verses from a single chapter. 'book' accepts full names,
    common abbreviations, or OSIS IDs. Case-insensitive."""
    conn = db.get_cached_connection(DB_PATH)
    rows = db.db_get_passage(conn, translation, book, chapter, verse_start, verse_end)
    if not rows:
        return {"error": f"No verses found: {translation} {book} {chapter}:{verse_start}-{verse_end}"}
    return {
        "translation": translation,
        "book": book,
        "chapter": chapter,
        "verses": [{"verse": r["verse"], "text": r["text"]} for r in rows],
    }


@mcp.tool
def search_text(translation: str, query: str, limit: int = 10,
                testament: str = None) -> dict:
    """Full-text keyword search across all verses in a translation.
    Optional 'testament' filters to 'old' or 'new' testament (also accepts 'OT'/'NT')."""
    t = db.resolve_testament(testament)
    if testament is not None and t is None:
        return {"error": f"Unknown testament: {testament!r}. Use 'old' or 'new'."}
    conn = db.get_cached_connection(DB_PATH)
    rows = db.db_search_text(conn, translation, query, limit, t)
    return {
        "results": [
            {
                "book": r["book"],
                "osis_id": r["osis_id"],
                "chapter": r["chapter"],
                "verse": r["verse"],
                "text": r["text"],
                "score": r["score"],
            }
            for r in rows
        ]
    }


@mcp.tool
def search_semantic(query: str, translation: str = "web", limit: int = 10,
                    testament: str = None) -> dict:
    """Semantic similarity search using sentence-transformer vector embeddings.
    Optional 'testament' filters to 'old' or 'new' testament (also accepts 'OT'/'NT')."""
    t = db.resolve_testament(testament)
    if testament is not None and t is None:
        return {"error": f"Unknown testament: {testament!r}. Use 'old' or 'new'."}
    conn = db.get_cached_connection(DB_PATH)
    rows = db.db_search_semantic(conn, query, translation, limit, t)
    return {
        "results": [
            {
                "book": r["book"],
                "osis_id": r["osis_id"],
                "chapter": r["chapter"],
                "verse": r["verse"],
                "text": r["text"],
                "distance": r["distance"],
            }
            for r in rows
        ]
    }


@mcp.tool
def list_translations() -> dict:
    """List all Bible translations available in the database."""
    conn = db.get_cached_connection(DB_PATH)
    rows = db.db_list_translations(conn)
    return {"translations": [dict(r) for r in rows]}


@mcp.tool
def list_books(translation: str) -> dict:
    """List all books for a given translation with testament grouping."""
    conn = db.get_cached_connection(DB_PATH)
    rows = db.db_list_books(conn, translation)
    if not rows:
        return {"error": f"Translation not found: {translation}"}
    return {"books": [dict(r) for r in rows]}


if __name__ == "__main__":
    mcp.run()
