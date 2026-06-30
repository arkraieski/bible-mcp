BOOKS = [
    # Old Testament
    ("Gen",   "Genesis",           "OT",  1),
    ("Exod",  "Exodus",            "OT",  2),
    ("Lev",   "Leviticus",         "OT",  3),
    ("Num",   "Numbers",           "OT",  4),
    ("Deut",  "Deuteronomy",       "OT",  5),
    ("Josh",  "Joshua",            "OT",  6),
    ("Judg",  "Judges",            "OT",  7),
    ("Ruth",  "Ruth",              "OT",  8),
    ("1Sam",  "1 Samuel",          "OT",  9),
    ("2Sam",  "2 Samuel",          "OT", 10),
    ("1Kgs",  "1 Kings",           "OT", 11),
    ("2Kgs",  "2 Kings",           "OT", 12),
    ("1Chr",  "1 Chronicles",      "OT", 13),
    ("2Chr",  "2 Chronicles",      "OT", 14),
    ("Ezra",  "Ezra",              "OT", 15),
    ("Neh",   "Nehemiah",          "OT", 16),
    ("Esth",  "Esther",            "OT", 17),
    ("Job",   "Job",               "OT", 18),
    ("Ps",    "Psalms",            "OT", 19),
    ("Prov",  "Proverbs",          "OT", 20),
    ("Eccl",  "Ecclesiastes",      "OT", 21),
    ("Song",  "Song of Solomon",   "OT", 22),
    ("Isa",   "Isaiah",            "OT", 23),
    ("Jer",   "Jeremiah",          "OT", 24),
    ("Lam",   "Lamentations",      "OT", 25),
    ("Ezek",  "Ezekiel",           "OT", 26),
    ("Dan",   "Daniel",            "OT", 27),
    ("Hos",   "Hosea",             "OT", 28),
    ("Joel",  "Joel",              "OT", 29),
    ("Amos",  "Amos",              "OT", 30),
    ("Obad",  "Obadiah",           "OT", 31),
    ("Jonah", "Jonah",             "OT", 32),
    ("Mic",   "Micah",             "OT", 33),
    ("Nah",   "Nahum",             "OT", 34),
    ("Hab",   "Habakkuk",          "OT", 35),
    ("Zeph",  "Zephaniah",         "OT", 36),
    ("Hag",   "Haggai",            "OT", 37),
    ("Zech",  "Zechariah",         "OT", 38),
    ("Mal",   "Malachi",           "OT", 39),
    # New Testament
    ("Matt",  "Matthew",           "NT", 40),
    ("Mark",  "Mark",              "NT", 41),
    ("Luke",  "Luke",              "NT", 42),
    ("John",  "John",              "NT", 43),
    ("Acts",  "Acts",              "NT", 44),
    ("Rom",   "Romans",            "NT", 45),
    ("1Cor",  "1 Corinthians",     "NT", 46),
    ("2Cor",  "2 Corinthians",     "NT", 47),
    ("Gal",   "Galatians",         "NT", 48),
    ("Eph",   "Ephesians",         "NT", 49),
    ("Phil",  "Philippians",       "NT", 50),
    ("Col",   "Colossians",        "NT", 51),
    ("1Thess","1 Thessalonians",   "NT", 52),
    ("2Thess","2 Thessalonians",   "NT", 53),
    ("1Tim",  "1 Timothy",         "NT", 54),
    ("2Tim",  "2 Timothy",         "NT", 55),
    ("Titus", "Titus",             "NT", 56),
    ("Phlm",  "Philemon",          "NT", 57),
    ("Heb",   "Hebrews",           "NT", 58),
    ("Jas",   "James",             "NT", 59),
    ("1Pet",  "1 Peter",           "NT", 60),
    ("2Pet",  "2 Peter",           "NT", 61),
    ("1John", "1 John",            "NT", 62),
    ("2John", "2 John",            "NT", 63),
    ("3John", "3 John",            "NT", 64),
    ("Jude",  "Jude",              "NT", 65),
    ("Rev",   "Revelation",        "NT", 66),
]

# Build alias map from OSIS IDs and full names
_ALIASES: dict[str, str] = {}
for _osis_id, _name, _, _ in BOOKS:
    _ALIASES[_osis_id.lower()] = _osis_id
    _ALIASES[_name.lower()] = _osis_id

# Numbered book variants: auto-generate "1st X", "first X", "i x" etc.
_ORDINAL_PREFIXES = {
    "1": ["1st", "first", "i"],
    "2": ["2nd", "second", "ii"],
    "3": ["3rd", "third", "iii"],
}
for _osis_id, _name, _, _ in BOOKS:
    _prefix = _osis_id[0]
    if _prefix in _ORDINAL_PREFIXES and _osis_id[1:].isalpha():
        _base = _name.split(" ", 1)[1].lower()
        for _alt in _ORDINAL_PREFIXES[_prefix]:
            _ALIASES[f"{_alt} {_base}"] = _osis_id
            _ALIASES[f"{_alt}{_base}"] = _osis_id

# Manually curated abbreviations and alternate names
_EXTRA: dict[str, str] = {
    # Genesis
    "ge": "Gen", "gn": "Gen",
    # Exodus
    "ex": "Exod", "exo": "Exod",
    # Leviticus
    "lv": "Lev", "le": "Lev",
    # Numbers
    "nm": "Num", "nb": "Num", "nu": "Num",
    # Deuteronomy
    "dt": "Deut", "de": "Deut",
    # Judges
    "jdg": "Judg", "jg": "Judg",
    # Samuel
    "1sa": "1Sam", "2sa": "2Sam",
    # Kings
    "1ki": "1Kgs", "2ki": "2Kgs",
    # Chronicles
    "1ch": "1Chr", "2ch": "2Chr",
    # Psalms
    "psalm": "Ps", "psa": "Ps", "pss": "Ps",
    # Ecclesiastes
    "ec": "Eccl", "qoh": "Eccl", "qoheleth": "Eccl",
    # Song of Solomon
    "song of songs": "Song", "sos": "Song", "ss": "Song",
    "canticles": "Song", "cant": "Song", "canticle of canticles": "Song",
    # Isaiah
    "is": "Isa",
    # Lamentations
    "la": "Lam",
    # Obadiah
    "ob": "Obad",
    # Jonah
    "jon": "Jonah",
    # Zephaniah
    "zep": "Zeph", "zp": "Zeph",
    # Haggai
    "hg": "Hag",
    # Zechariah
    "zec": "Zech", "zc": "Zech",
    # Malachi
    "ml": "Mal",
    # Matthew
    "mt": "Matt",
    # Mark
    "mk": "Mark", "mr": "Mark",
    # Luke
    "lk": "Luke",
    # John
    "jn": "John", "joh": "John",
    # Acts
    "ac": "Acts",
    # Romans
    "ro": "Rom", "rm": "Rom",
    # Corinthians
    "1co": "1Cor", "2co": "2Cor",
    # Galatians
    "ga": "Gal",
    # Ephesians
    "ep": "Eph",
    # Philippians
    "php": "Phil", "pp": "Phil",
    # Colossians
    "co": "Col",
    # Thessalonians
    "1th": "1Thess", "2th": "2Thess",
    "1thes": "1Thess", "2thes": "2Thess",
    # Timothy
    "1ti": "1Tim", "2ti": "2Tim",
    # Titus
    "ti": "Titus",
    # Philemon
    "phm": "Phlm", "pm": "Phlm",
    # Hebrews
    "he": "Heb",
    # James
    "ja": "Jas", "jm": "Jas",
    # Peter
    "1pe": "1Pet", "2pe": "2Pet",
    # John epistles
    "1jn": "1John", "2jn": "2John", "3jn": "3John",
    "1jo": "1John", "2jo": "2John", "3jo": "3John",
    # Jude
    "jud": "Jude",
    # Revelation
    "revelations": "Rev", "apocalypse": "Rev", "re": "Rev",
}
_ALIASES.update({k.lower(): v for k, v in _EXTRA.items()})


OSIS_TO_NAME: dict[str, str] = {osis_id: name for osis_id, name, _, _ in BOOKS}


def resolve_book(name: str) -> str | None:
    """Resolve any book name, abbreviation, or OSIS ID to its canonical OSIS ID.

    Accepts full names ('Genesis'), common abbreviations ('Gen', 'ge', 'gn'),
    alternate names ('Song of Songs'), ordinal variants ('First Samuel',
    '1st Samuel', 'I Samuel'), and OSIS IDs directly. Case-insensitive.
    Returns None if the name cannot be resolved.
    """
    return _ALIASES.get(name.strip().lower())
