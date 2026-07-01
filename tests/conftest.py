import sys
from pathlib import Path

import pytest
import sqlite3
import sqlite_vec

sys.path.insert(0, str(Path(__file__).parent.parent))

import db as dbmod


@pytest.fixture(scope="session")
def conn():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")

    dbmod.init_schema(connection)

    connection.execute(
        "INSERT INTO translations (abbreviation, name, language, license) VALUES (?, ?, ?, ?)",
        ("web", "World English Bible", "en", "Public Domain"),
    )
    connection.commit()
    trans_id = connection.execute(
        "SELECT id FROM translations WHERE abbreviation = 'web'"
    ).fetchone()[0]

    test_books = [
        (trans_id, "Gen",   "Genesis",  "OT",  1),
        (trans_id, "Ps",    "Psalms",   "OT", 19),
        (trans_id, "John",  "John",     "NT", 43),
        (trans_id, "Rom",   "Romans",   "NT", 45),
        (trans_id, "1John", "1 John",   "NT", 62),
    ]
    connection.executemany(
        "INSERT INTO books (translation_id, osis_id, name, testament, book_order) VALUES (?, ?, ?, ?, ?)",
        test_books,
    )
    connection.commit()

    book_ids = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT osis_id, id FROM books WHERE translation_id = ?", (trans_id,)
        )
    }

    test_verses = [
        (trans_id, book_ids["Gen"],   1,  1, "In the beginning, God created the heavens and the earth."),
        (trans_id, book_ids["Gen"],   1,  2, "The earth was formless and empty. Darkness was on the surface of the deep."),
        (trans_id, book_ids["Ps"],   23,  1, "The LORD is my shepherd; I shall not want."),
        (trans_id, book_ids["John"],  3, 16, "For God so loved the world, that he gave his only Son."),
        (trans_id, book_ids["John"],  3, 17, "For God didn't send his Son into the world to judge the world."),
        (trans_id, book_ids["Rom"],   5,  8, "But God commends his own love toward us."),
        (trans_id, book_ids["1John"], 4,  9, "By this was God's love revealed in us."),
    ]
    connection.executemany(
        "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
        test_verses,
    )
    connection.commit()

    connection.execute("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")
    connection.commit()

    verse_ids = [row[0] for row in connection.execute("SELECT id FROM verses").fetchall()]
    for i, vid in enumerate(verse_ids):
        emb = [0.0] * 384
        emb[i % 384] = 1.0
        connection.execute(
            "INSERT INTO verse_embeddings (verse_id, embedding) VALUES (?, ?)",
            (vid, sqlite_vec.serialize_float32(emb)),
        )
    connection.commit()

    test_cross_refs = [
        ("John", 3, 16, "Rom",   5,  8,  8, 974),
        ("John", 3, 16, "1John", 4,  9,  9, 690),
        ("John", 3, 16, "Gen",   1,  1,  1, 100),
        ("Gen",  1,  1, "John",  3, 16, 16,  50),
    ]
    connection.executemany(
        """INSERT INTO cross_references
           (from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        test_cross_refs,
    )
    connection.commit()

    return connection
