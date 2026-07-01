import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ingest_cross_references import _parse_bcv, _parse_to_ref, parse_tsv


class TestParseBcv:
    def test_valid_reference(self):
        assert _parse_bcv("Gen.1.1") == ("Gen", 1, 1)
        assert _parse_bcv("John.3.16") == ("John", 3, 16)
        assert _parse_bcv("Rev.22.21") == ("Rev", 22, 21)

    def test_resolves_book_aliases(self):
        # OpenBible.info uses OSIS IDs; ensure they resolve correctly
        assert _parse_bcv("Ps.23.1") == ("Ps", 23, 1)
        assert _parse_bcv("1Sam.1.1") == ("1Sam", 1, 1)

    def test_unknown_book_returns_none(self):
        assert _parse_bcv("Hezekiah.1.1") is None

    def test_non_numeric_chapter_returns_none(self):
        assert _parse_bcv("Gen.a.1") is None

    def test_non_numeric_verse_returns_none(self):
        assert _parse_bcv("Gen.1.b") is None

    def test_wrong_segment_count_returns_none(self):
        assert _parse_bcv("Gen.1") is None
        assert _parse_bcv("Gen") is None
        assert _parse_bcv("Gen.1.1.extra") is None


class TestParseToRef:
    def test_single_verse(self):
        assert _parse_to_ref("Rom.5.8") == ("Rom", 5, 8, 8)

    def test_same_chapter_range(self):
        assert _parse_to_ref("Gen.1.1-Gen.1.3") == ("Gen", 1, 1, 3)

    def test_cross_chapter_range_collapses_to_start_verse(self):
        result = _parse_to_ref("John.3.16-John.4.2")
        assert result == ("John", 3, 16, 16)

    def test_unknown_book_returns_none(self):
        assert _parse_to_ref("Hezekiah.1.1") is None

    def test_invalid_range_end_returns_none(self):
        assert _parse_to_ref("Gen.1.1-Hezekiah.1.1") is None


class TestParseTsv:
    SAMPLE_TSV = "\n".join([
        "From Verse\tTo Verse\tVotes",
        "Gen.1.1\tJohn.1.1\t42",
        "John.3.16\tRom.5.8\t974",
        "John.3.16\t1John.4.9-1John.4.10\t690",
        "John.3.16\tHezekiah.1.1\t5",   # invalid book — skipped
        "badline",                         # malformed — skipped
        "",                                # blank — skipped
    ])

    def test_parses_valid_rows(self):
        records = parse_tsv(self.SAMPLE_TSV.encode())
        assert len(records) == 3

    def test_record_structure(self):
        records = parse_tsv(self.SAMPLE_TSV.encode())
        from_book, from_ch, from_v, to_book, to_ch, to_vs, to_ve, votes = records[0]
        assert from_book == "Gen"
        assert from_ch == 1
        assert from_v == 1
        assert to_book == "John"
        assert votes == 42

    def test_range_record(self):
        records = parse_tsv(self.SAMPLE_TSV.encode())
        # third valid row: 1John.4.9-1John.4.10
        _, _, _, _, _, vs, ve, _ = records[2]
        assert vs == 9
        assert ve == 10

    def test_skips_header(self):
        records = parse_tsv(self.SAMPLE_TSV.encode())
        # header line should not appear as a record
        assert all(r[0] != "From Verse" for r in records)

    def test_empty_input(self):
        records = parse_tsv(b"From Verse\tTo Verse\tVotes\n")
        assert records == []
