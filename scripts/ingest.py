"""
Parse an OSIS XML Bible file into the bible.db SQLite database,
including FTS5 indexing and sentence-transformer embeddings.

Usage:
    python scripts/ingest.py --file data/web.xml --translation web \
        --name "World English Bible" --license "Public Domain"
"""

import argparse
import sys
from pathlib import Path

# Allow importing db.py from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite_vec
from lxml import etree
from sentence_transformers import SentenceTransformer

import db as dbmod

# Canonical 66-book ordering: (osis_id, name, testament, book_order)
BOOKS = [
    # Old Testament
    ("Gen",  "Genesis",          "OT",  1),
    ("Exod", "Exodus",           "OT",  2),
    ("Lev",  "Leviticus",        "OT",  3),
    ("Num",  "Numbers",          "OT",  4),
    ("Deut", "Deuteronomy",      "OT",  5),
    ("Josh", "Joshua",           "OT",  6),
    ("Judg", "Judges",           "OT",  7),
    ("Ruth", "Ruth",             "OT",  8),
    ("1Sam", "1 Samuel",         "OT",  9),
    ("2Sam", "2 Samuel",         "OT", 10),
    ("1Kgs", "1 Kings",          "OT", 11),
    ("2Kgs", "2 Kings",          "OT", 12),
    ("1Chr", "1 Chronicles",     "OT", 13),
    ("2Chr", "2 Chronicles",     "OT", 14),
    ("Ezra", "Ezra",             "OT", 15),
    ("Neh",  "Nehemiah",         "OT", 16),
    ("Esth", "Esther",           "OT", 17),
    ("Job",  "Job",              "OT", 18),
    ("Ps",   "Psalms",           "OT", 19),
    ("Prov", "Proverbs",         "OT", 20),
    ("Eccl", "Ecclesiastes",     "OT", 21),
    ("Song", "Song of Solomon",  "OT", 22),
    ("Isa",  "Isaiah",           "OT", 23),
    ("Jer",  "Jeremiah",         "OT", 24),
    ("Lam",  "Lamentations",     "OT", 25),
    ("Ezek", "Ezekiel",          "OT", 26),
    ("Dan",  "Daniel",           "OT", 27),
    ("Hos",  "Hosea",            "OT", 28),
    ("Joel", "Joel",             "OT", 29),
    ("Amos", "Amos",             "OT", 30),
    ("Obad", "Obadiah",          "OT", 31),
    ("Jonah","Jonah",            "OT", 32),
    ("Mic",  "Micah",            "OT", 33),
    ("Nah",  "Nahum",            "OT", 34),
    ("Hab",  "Habakkuk",         "OT", 35),
    ("Zeph", "Zephaniah",        "OT", 36),
    ("Hag",  "Haggai",           "OT", 37),
    ("Zech", "Zechariah",        "OT", 38),
    ("Mal",  "Malachi",          "OT", 39),
    # New Testament
    ("Matt", "Matthew",          "NT", 40),
    ("Mark", "Mark",             "NT", 41),
    ("Luke", "Luke",             "NT", 42),
    ("John", "John",             "NT", 43),
    ("Acts", "Acts",             "NT", 44),
    ("Rom",  "Romans",           "NT", 45),
    ("1Cor", "1 Corinthians",    "NT", 46),
    ("2Cor", "2 Corinthians",    "NT", 47),
    ("Gal",  "Galatians",        "NT", 48),
    ("Eph",  "Ephesians",        "NT", 49),
    ("Phil", "Philippians",      "NT", 50),
    ("Col",  "Colossians",       "NT", 51),
    ("1Thess","1 Thessalonians", "NT", 52),
    ("2Thess","2 Thessalonians", "NT", 53),
    ("1Tim", "1 Timothy",        "NT", 54),
    ("2Tim", "2 Timothy",        "NT", 55),
    ("Titus","Titus",            "NT", 56),
    ("Phlm", "Philemon",         "NT", 57),
    ("Heb",  "Hebrews",          "NT", 58),
    ("Jas",  "James",            "NT", 59),
    ("1Pet", "1 Peter",          "NT", 60),
    ("2Pet", "2 Peter",          "NT", 61),
    ("1John","1 John",           "NT", 62),
    ("2John","2 John",           "NT", 63),
    ("3John","3 John",           "NT", 64),
    ("Jude", "Jude",             "NT", 65),
    ("Rev",  "Revelation",       "NT", 66),
]

BOOK_INFO = {b[0]: b for b in BOOKS}


def local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def extract_verse_text(verse_elem) -> str:
    parts = []
    if verse_elem.text:
        parts.append(verse_elem.text)
    for child in verse_elem:
        tag = local(child.tag)
        if tag == "note":
            # Skip footnote content; keep text that follows the closing tag
            pass
        else:
            parts.extend(child.itertext())
        if child.tail:
            parts.append(child.tail)
    return " ".join("".join(parts).split())


def parse_osis(xml_path: str) -> list[tuple]:
    """
    Returns list of (book_osis_id, chapter, verse_num, text) tuples.
    Uses iterparse for memory efficiency on large XML files.
    """
    print(f"Parsing {xml_path} ...")
    verses = []
    current_book = None
    current_chapter = None

    context = etree.iterparse(xml_path, events=("start", "end"))
    for event, elem in context:
        tag = local(elem.tag)

        if event == "start":
            if tag == "div" and elem.get("type") == "book":
                current_book = elem.get("osisID")
            elif tag == "chapter":
                osis_ref = elem.get("osisID", "")
                parts = osis_ref.split(".")
                if len(parts) >= 2:
                    try:
                        current_chapter = int(parts[1])
                    except ValueError:
                        pass

        elif event == "end":
            if tag == "verse":
                osis_ref = elem.get("osisID", "")
                parts = osis_ref.split(".")
                if len(parts) == 3 and current_book:
                    try:
                        verse_num = int(parts[2])
                        text = extract_verse_text(elem)
                        if text:
                            verses.append((current_book, current_chapter, verse_num, text))
                    except ValueError:
                        pass
                elem.clear()

    print(f"  Parsed {len(verses)} verses.")
    return verses


def ingest(args) -> None:
    conn = dbmod.get_connection(args.db)
    dbmod.init_schema(conn)

    # Upsert translation
    conn.execute(
        "INSERT OR IGNORE INTO translations (abbreviation, name, language, license) VALUES (?, ?, ?, ?)",
        (args.translation, args.name, args.language, args.license),
    )
    conn.commit()
    translation_id = conn.execute(
        "SELECT id FROM translations WHERE abbreviation = ?", (args.translation,)
    ).fetchone()[0]
    print(f"Translation '{args.translation}' → id={translation_id}")

    # Insert books (idempotent)
    for osis_id, name, testament, book_order in BOOKS:
        conn.execute(
            """INSERT OR IGNORE INTO books
               (translation_id, osis_id, name, testament, book_order)
               VALUES (?, ?, ?, ?, ?)""",
            (translation_id, osis_id, name, testament, book_order),
        )
    conn.commit()

    book_id_map = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT osis_id, id FROM books WHERE translation_id = ?", (translation_id,)
        ).fetchall()
    }

    # Parse XML
    raw_verses = parse_osis(args.file)

    # Insert verses in a single transaction
    print("Inserting verses ...")
    skipped = 0
    inserted = 0
    conn.execute("BEGIN")
    for book_osis, chapter, verse_num, text in raw_verses:
        book_id = book_id_map.get(book_osis)
        if book_id is None:
            skipped += 1
            continue
        conn.execute(
            """INSERT OR IGNORE INTO verses
               (translation_id, book_id, chapter, verse, text)
               VALUES (?, ?, ?, ?, ?)""",
            (translation_id, book_id, chapter, verse_num, text),
        )
        inserted += 1
    conn.execute("COMMIT")
    print(f"  {inserted} verses processed ({skipped} skipped — unknown book IDs).")

    # Rebuild FTS index
    print("Rebuilding FTS5 index ...")
    conn.execute("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")
    conn.commit()
    print("  FTS5 index rebuilt.")

    # Generate embeddings for any verses missing them
    rows = conn.execute(
        """
        SELECT v.id, v.text FROM verses v
        LEFT JOIN verse_embeddings ve ON ve.verse_id = v.id
        WHERE v.translation_id = ? AND ve.verse_id IS NULL
        """,
        (translation_id,),
    ).fetchall()

    if not rows:
        print("All embeddings already present — skipping.")
        return

    print(f"Generating embeddings for {len(rows)} verses (this will take several minutes) ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts = [r[1] for r in rows]
    ids = [r[0] for r in rows]

    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    print("Storing embeddings ...")
    conn.executemany(
        "INSERT OR REPLACE INTO verse_embeddings (verse_id, embedding) VALUES (?, ?)",
        [
            (vid, sqlite_vec.serialize_float32(emb.tolist()))
            for vid, emb in zip(ids, embeddings)
        ],
    )
    conn.commit()
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Ingest an OSIS XML Bible file into bible.db")
    parser.add_argument("--file", required=True, help="Path to the OSIS XML file")
    parser.add_argument("--translation", required=True, help="Translation abbreviation (e.g. web)")
    parser.add_argument("--name", required=True, help="Full translation name")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--license", default=None, help="License text")
    parser.add_argument("--db", default="bible.db", help="Path to SQLite database (default: bible.db)")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    ingest(args)


if __name__ == "__main__":
    main()
