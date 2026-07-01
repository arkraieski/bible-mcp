from books import resolve_book, OSIS_TO_NAME, BOOKS


class TestResolveBook:
    def test_canonical_osis_ids(self):
        assert resolve_book("Gen") == "Gen"
        assert resolve_book("Matt") == "Matt"
        assert resolve_book("Rev") == "Rev"
        assert resolve_book("1Sam") == "1Sam"
        assert resolve_book("Ps") == "Ps"

    def test_full_names(self):
        assert resolve_book("Genesis") == "Gen"
        assert resolve_book("Matthew") == "Matt"
        assert resolve_book("Revelation") == "Rev"
        assert resolve_book("Psalms") == "Ps"
        assert resolve_book("Song of Solomon") == "Song"

    def test_case_insensitive(self):
        assert resolve_book("genesis") == "Gen"
        assert resolve_book("GENESIS") == "Gen"
        assert resolve_book("gEnEsIs") == "Gen"
        assert resolve_book("matt") == "Matt"

    def test_common_abbreviations(self):
        assert resolve_book("ge") == "Gen"
        assert resolve_book("gn") == "Gen"
        assert resolve_book("ex") == "Exod"
        assert resolve_book("mt") == "Matt"
        assert resolve_book("mk") == "Mark"
        assert resolve_book("jn") == "John"
        assert resolve_book("psa") == "Ps"

    def test_ordinal_variants(self):
        assert resolve_book("First Samuel") == "1Sam"
        assert resolve_book("1st Samuel") == "1Sam"
        assert resolve_book("I Samuel") == "1Sam"
        assert resolve_book("Second Kings") == "2Kgs"
        assert resolve_book("2nd Kings") == "2Kgs"
        assert resolve_book("Third John") == "3John"

    def test_alternate_names(self):
        assert resolve_book("Song of Songs") == "Song"
        assert resolve_book("Qoheleth") == "Eccl"
        assert resolve_book("Revelations") == "Rev"
        assert resolve_book("Canticles") == "Song"

    def test_whitespace_stripped(self):
        assert resolve_book("  Genesis  ") == "Gen"

    def test_unknown_returns_none(self):
        assert resolve_book("Hezekiah") is None
        assert resolve_book("") is None
        assert resolve_book("42") is None


class TestOsisToName:
    def test_spot_check(self):
        assert OSIS_TO_NAME["Gen"] == "Genesis"
        assert OSIS_TO_NAME["Matt"] == "Matthew"
        assert OSIS_TO_NAME["Rev"] == "Revelation"
        assert OSIS_TO_NAME["1Sam"] == "1 Samuel"

    def test_covers_all_66_books(self):
        assert len(OSIS_TO_NAME) == len(BOOKS) == 66

    def test_all_osis_ids_resolve_to_themselves(self):
        for osis_id, _, _, _ in BOOKS:
            assert resolve_book(osis_id) == osis_id
