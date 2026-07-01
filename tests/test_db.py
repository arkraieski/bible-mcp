import numpy as np
import pytest
import sqlite_vec

import db as dbmod


class _FakeModel:
    def encode(self, text, convert_to_numpy=True, **kwargs):
        return np.zeros(384, dtype=np.float32)


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(dbmod, "_model", _FakeModel())


class TestResolveTestament:
    def test_old_testament_variants(self):
        assert dbmod.resolve_testament("old") == "OT"
        assert dbmod.resolve_testament("OT") == "OT"
        assert dbmod.resolve_testament("Old Testament") == "OT"

    def test_new_testament_variants(self):
        assert dbmod.resolve_testament("new") == "NT"
        assert dbmod.resolve_testament("NT") == "NT"
        assert dbmod.resolve_testament("New Testament") == "NT"

    def test_none_passthrough(self):
        assert dbmod.resolve_testament(None) is None

    def test_unknown_returns_none(self):
        assert dbmod.resolve_testament("middle") is None


class TestGetVerse:
    def test_found(self, conn):
        row = dbmod.db_get_verse(conn, "web", "John", 3, 16)
        assert row is not None
        assert "loved the world" in row["text"]
        assert row["chapter"] == 3
        assert row["verse"] == 16

    def test_accepts_full_book_name(self, conn):
        row = dbmod.db_get_verse(conn, "web", "Genesis", 1, 1)
        assert row is not None
        assert row["osis_id"] == "Gen"

    def test_case_insensitive_book(self, conn):
        assert dbmod.db_get_verse(conn, "web", "genesis", 1, 1) is not None

    def test_verse_not_found(self, conn):
        assert dbmod.db_get_verse(conn, "web", "Gen", 1, 999) is None

    def test_unknown_book_returns_none(self, conn):
        assert dbmod.db_get_verse(conn, "web", "Hezekiah", 1, 1) is None

    def test_unknown_translation_returns_none(self, conn):
        assert dbmod.db_get_verse(conn, "kjv", "Gen", 1, 1) is None


class TestGetPassage:
    def test_single_verse_range(self, conn):
        rows = dbmod.db_get_passage(conn, "web", "Gen", 1, 1, 1)
        assert len(rows) == 1
        assert "beginning" in rows[0]["text"]

    def test_multi_verse_range(self, conn):
        rows = dbmod.db_get_passage(conn, "web", "Gen", 1, 1, 2)
        assert len(rows) == 2
        assert rows[0]["verse"] == 1
        assert rows[1]["verse"] == 2

    def test_range_beyond_available_verses(self, conn):
        rows = dbmod.db_get_passage(conn, "web", "Gen", 1, 1, 99)
        assert len(rows) == 2  # only 2 Gen verses in fixture

    def test_empty_for_missing_chapter(self, conn):
        assert dbmod.db_get_passage(conn, "web", "Gen", 99, 1, 5) == []

    def test_unknown_book_returns_empty(self, conn):
        assert dbmod.db_get_passage(conn, "web", "Hezekiah", 1, 1, 5) == []


class TestSearchText:
    def test_basic_search(self, conn):
        rows = dbmod.db_search_text(conn, "web", "shepherd", 10)
        assert len(rows) >= 1
        assert any("shepherd" in r["text"].lower() for r in rows)

    def test_returns_book_metadata(self, conn):
        rows = dbmod.db_search_text(conn, "web", "shepherd", 10)
        assert rows[0]["book"] is not None
        assert rows[0]["osis_id"] is not None

    def test_testament_filter_ot(self, conn):
        rows = dbmod.db_search_text(conn, "web", "God", 10, testament="OT")
        for r in rows:
            assert r["osis_id"] in ("Gen", "Ps")

    def test_testament_filter_nt(self, conn):
        rows = dbmod.db_search_text(conn, "web", "God", 10, testament="NT")
        for r in rows:
            assert r["osis_id"] in ("John", "Rom", "1John")

    def test_no_results(self, conn):
        rows = dbmod.db_search_text(conn, "web", "xyzzy", 10)
        assert rows == []


class TestSearchSemantic:
    def test_returns_results(self, conn, fake_model):
        rows = dbmod.db_search_semantic(conn, "love", "web", 5)
        assert len(rows) > 0

    def test_testament_filter_ot(self, conn, fake_model):
        rows = dbmod.db_search_semantic(conn, "creation", "web", 10, testament="OT")
        for r in rows:
            assert r["osis_id"] in ("Gen", "Ps")

    def test_testament_filter_nt(self, conn, fake_model):
        rows = dbmod.db_search_semantic(conn, "love", "web", 10, testament="NT")
        for r in rows:
            assert r["osis_id"] in ("John", "Rom", "1John")

    def test_returns_expected_fields(self, conn, fake_model):
        rows = dbmod.db_search_semantic(conn, "love", "web", 3)
        for r in rows:
            assert "book" in r.keys()
            assert "chapter" in r.keys()
            assert "verse" in r.keys()
            assert "text" in r.keys()
            assert "distance" in r.keys()


class TestGetCrossReferences:
    def test_basic_lookup(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, None, 10)
        assert len(refs) == 3
        assert refs[0]["votes"] >= refs[1]["votes"]  # sorted by votes desc

    def test_includes_verse_text(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, None, 10)
        for ref in refs:
            assert "verses" in ref
            assert len(ref["verses"]) > 0

    def test_min_votes_filter(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, 500, 10)
        assert all(r["votes"] >= 500 for r in refs)

    def test_limit(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, None, 1)
        assert len(refs) == 1

    def test_testament_filter_nt(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, None, 10, testament="NT")
        for r in refs:
            assert r["osis_id"] in ("John", "Rom", "1John")

    def test_testament_filter_ot(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "John", 3, 16, None, 10, testament="OT")
        for r in refs:
            assert r["osis_id"] in ("Gen", "Ps")

    def test_no_refs_for_unknown_verse(self, conn):
        refs = dbmod.db_get_cross_references(conn, "web", "Ps", 23, 1, None, 10)
        assert refs == []


class TestListTranslations:
    def test_returns_list(self, conn):
        rows = dbmod.db_list_translations(conn)
        assert len(rows) >= 1

    def test_contains_web(self, conn):
        rows = dbmod.db_list_translations(conn)
        abbrevs = [r["abbreviation"] for r in rows]
        assert "web" in abbrevs


class TestListBooks:
    def test_returns_books_for_translation(self, conn):
        rows = dbmod.db_list_books(conn, "web")
        assert len(rows) == 5  # matches fixture

    def test_ordered_by_book_order(self, conn):
        rows = dbmod.db_list_books(conn, "web")
        orders = [r["book_order"] for r in rows]
        assert orders == sorted(orders)

    def test_unknown_translation_returns_empty(self, conn):
        assert dbmod.db_list_books(conn, "kjv") == []
