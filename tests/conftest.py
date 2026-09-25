import sqlite3

import pytest

SCHEMA = """
CREATE TABLE person (id TEXT PRIMARY KEY, first_name TEXT, last_name TEXT, party TEXT, is_mdb INTEGER);
CREATE TABLE sitting (id TEXT PRIMARY KEY, wahlperiode INTEGER, number INTEGER, date TEXT, pdf_url TEXT);
CREATE TABLE agenda_item (id TEXT PRIMARY KEY, sitting_id TEXT, top_id TEXT, title TEXT, drucksache_numbers TEXT);
CREATE TABLE speech (id TEXT PRIMARY KEY, sitting_id TEXT, agenda_item_id TEXT, position INTEGER, person_id TEXT,
    speaker_name TEXT, speaker_role TEXT, fraction TEXT, text TEXT, source_document_id TEXT);
CREATE TABLE speech_paragraph (id TEXT PRIMARY KEY, speech_id TEXT, position INTEGER, kind TEXT, text TEXT);
"""

LONG = "Wohnen ist die soziale Frage unserer Zeit. " * 15  # > 500 chars
PLPR = "BT-PlPr. 21/88"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    c.executemany(
        "INSERT INTO person VALUES (?,?,?,?,?)",
        [
            ("1", "Anna", "Adler", "SPD", 1),
            ("2", "Bernd", "Berg", "CSU", 1),
            ("3", "Clara", "Cohn", "DIE LINKE.", 1),
            ("9", "Stefanie", "Hubig", None, 0),
        ],
    )
    c.executemany(
        "INSERT INTO sitting VALUES (?,?,?,?,?)",
        [
            ("21/88", 21, 88, "2026-07-08", "https://x/21088.pdf"),
            ("21/89", 21, 89, "2026-07-09", "https://x/21089.pdf"),
            ("21/91", 21, 91, "2026-09-08", "https://x/21091.pdf"),
        ],
    )
    c.executemany(
        "INSERT INTO agenda_item VALUES (?,?,?,?,?)",
        [
            ("21/88/1", "21/88", "Tagesordnungspunkt 1", "Befragung der Bundesregierung", "[]"),
            (
                "21/88/2",
                "21/88",
                "Tagesordnungspunkt 2",
                "Beratung des Antrags der Abgeordneten X, Y und der Fraktion Die Linke | Mietpreisbremse verlängern",
                '["21/100"]',
            ),
            ("21/91/1", "21/91", "Einzelplan 04", None, "[]"),
        ],
    )
    # a Zwischenfrage: rede ID1 split into ID1 (Berg), ID1-2 (Cohn asks), ID1-3 (Berg answers)
    c.executemany(
        "INSERT INTO speech VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("ID0", "21/88", "21/88/1", 1, "9", "Stefanie Hubig, Bundesministerin", "Ministerin", None, LONG, PLPR),
            ("ID1", "21/88", "21/88/2", 2, "2", "Bernd Berg (CDU/CSU)", None, "CDU/CSU", LONG, PLPR),
            ("ID1-2", "21/88", "21/88/2", 3, "3", "Clara Cohn (Die Linke)", None, "Die Linke", "Kurze Frage?", PLPR),
            ("ID1-3", "21/88", "21/88/2", 4, "2", "Bernd Berg (CDU/CSU)", None, "CDU/CSU", "Kurze Antwort.", PLPR),
            ("ID2", "21/89", "21/88/2", 1, "1", "Anna Adler, Ministerin", "Ministerin", None, LONG, "BT-PlPr. 21/89"),
            ("ID3", "21/91", "21/91/1", 1, "1", "Anna Adler (SPD)", None, "SPD", LONG, "BT-PlPr. 21/91"),
        ],
    )  # fmt: skip
    c.executemany(
        "INSERT INTO speech_paragraph VALUES (?,?,?,?,?)",
        [
            ("ID1/1", "ID1", 1, "text", LONG),
            ("ID1/2", "ID1", 2, "comment", "(Beifall)"),
            ("ID1/3", "ID1", 3, "chair", "Zwischenfrage?"),
            ("ID1-2/1", "ID1-2", 1, "text", "Kurze Frage?"),
            ("ID1-3/1", "ID1-3", 1, "text", "Kurze Antwort."),
            ("ID0/1", "ID0", 1, "text", LONG),
            ("ID2/1", "ID2", 1, "text", LONG),
            ("ID3/1", "ID3", 1, "text", LONG),
        ],
    )
    return c
