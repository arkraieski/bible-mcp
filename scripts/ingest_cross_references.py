"""
Download and ingest the OpenBible.info cross-reference dataset into bible.db.

Data: OpenBible.info (CC-BY), derived from the public-domain
Treasury of Scripture Knowledge (TSK). See https://openbible.info/source.htm

Usage:
    python scripts/ingest_cross_references.py
    python scripts/ingest_cross_references.py --db /path/to/bible.db
"""

import argparse
import io
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).parent.parent))

import db as dbmod
from books import resolve_book

CROSS_REF_URL = "https://a.openbible.info/data/cross-references.zip"


def download_zip(url: str) -> bytes:
    print(f"Downloading {url} ...")
    try:
        with urlopen(url) as response:
            data = response.read()
    except URLError as e:
        print(f"ERROR: Download failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  Downloaded {len(data):,} bytes.")
    return data


def _parse_bcv(ref: str) -> tuple[str, int, int] | None:
    """Parse 'Book.Chapter.Verse' → (osis_id, chapter, verse)."""
    parts = ref.strip().split(".")
    if len(parts) != 3:
        return None
    osis_id = resolve_book(parts[0])
    if osis_id is None:
        return None
    try:
        return osis_id, int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _parse_to_ref(to_ref: str) -> tuple[str, int, int, int] | None:
    """
    Parse a 'to' reference, which may be a single verse ('Gen.1.1') or a
    range ('Gen.1.1-Gen.1.3'). Cross-chapter ranges are reduced to the
    start verse so the single-chapter passage model stays clean.
    """
    if "-" in to_ref:
        start_str, end_str = to_ref.split("-", 1)
        start = _parse_bcv(start_str)
        end = _parse_bcv(end_str)
        if start is None or end is None:
            return None
        osis_id, chapter, verse_start = start
        _, end_chapter, verse_end = end
        if end_chapter != chapter:
            # Cross-chapter range: keep only the start verse
            verse_end = verse_start
    else:
        result = _parse_bcv(to_ref)
        if result is None:
            return None
        osis_id, chapter, verse_start = result
        verse_end = verse_start
    return osis_id, chapter, verse_start, verse_end


def parse_tsv(data: bytes) -> list[tuple]:
    """
    Returns list of
    (from_book, from_chapter, from_verse, to_book, to_chapter, to_verse_start, to_verse_end, votes).
    """
    records = []
    skipped = 0

    lines = data.decode("utf-8").splitlines()
    if lines and lines[0].lower().startswith("from"):
        lines = lines[1:]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            skipped += 1
            continue

        from_ref, to_ref, votes_str = parts[0], parts[1], parts[2]

        from_parsed = _parse_bcv(from_ref)
        if from_parsed is None:
            skipped += 1
            continue

        to_parsed = _parse_to_ref(to_ref)
        if to_parsed is None:
            skipped += 1
            continue

        try:
            votes = int(votes_str)
        except ValueError:
            votes = 0

        from_book, from_chapter, from_verse = from_parsed
        to_book, to_chapter, to_verse_start, to_verse_end = to_parsed
        records.append((from_book, from_chapter, from_verse,
                         to_book, to_chapter, to_verse_start, to_verse_end, votes))

    print(f"  Parsed {len(records):,} cross-references ({skipped} skipped).")
    return records


def ingest(args) -> None:
    conn = dbmod.get_connection(args.db)
    dbmod.init_schema(conn)

    zip_data = download_zip(CROSS_REF_URL)

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        names = zf.namelist()
        tsv_name = next(
            (n for n in names if n.endswith(".txt") or n.endswith(".tsv")), None
        )
        if tsv_name is None:
            print(f"ERROR: No .txt/.tsv file found in zip (contents: {names})", file=sys.stderr)
            sys.exit(1)
        print(f"  Extracting {tsv_name} ...")
        tsv_data = zf.read(tsv_name)

    records = parse_tsv(tsv_data)
    if not records:
        print("ERROR: No records parsed — aborting.", file=sys.stderr)
        sys.exit(1)

    print("Inserting cross-references (replacing any existing data) ...")
    conn.execute("BEGIN")
    conn.execute("DELETE FROM cross_references")
    conn.executemany(
        """INSERT INTO cross_references
           (from_book, from_chapter, from_verse,
            to_book, to_chapter, to_verse_start, to_verse_end, votes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        records,
    )
    conn.execute("COMMIT")
    print(f"  Stored {len(records):,} cross-references.")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest OpenBible.info cross-references into bible.db"
    )
    parser.add_argument(
        "--db", default="bible.db",
        help="Path to the SQLite database (default: bible.db)"
    )
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: Database not found at {args.db}", file=sys.stderr)
        print("Run scripts/ingest.py first to create the database.", file=sys.stderr)
        sys.exit(1)

    ingest(args)


if __name__ == "__main__":
    main()
