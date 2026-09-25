from landscape import corpus


def test_weeks_are_iso_weeks(conn):
    w = corpus.weeks(conn)
    assert [x["week"] for x in w] == ["2026-W28", "2026-W37"]
    assert w[0]["sittings"] == [88, 89] and w[0]["speeches"] == 5


def test_week_range():
    assert corpus.week_range("2026-W28") == ("2026-07-06", "2026-07-12")
    assert corpus.week_id("2026-07-10") == "2026-W28"


def test_load_week_rejoins_splits_and_fills_fraction(conn):
    speeches = corpus.load_week(conn, "2026-W28")
    by_id = {s.id: s for s in speeches}
    assert set(by_id) == {"ID0", "ID1", "ID2"}  # ID1-2 is a short question, ID1-3 merged into ID1
    berg = by_id["ID1"]
    assert berg.part_ids == ["ID1", "ID1-3"] and berg.text.endswith("Kurze Antwort.")
    assert [k for k, _ in berg.paragraphs] == ["text", "comment", "chair", "zwischenfrage", "text"]
    assert berg.paragraphs[3] == ("zwischenfrage", "ID1-2") and berg.n_comments == 1
    assert berg.linked["ID1-2"]["paragraphs"] == [("text", "Kurze Frage?"), ("antwort", "ID1")]
    assert berg.start == ("2026-07-08", 2) and berg.end == ("2026-07-08", 4)
    assert berg.speaker == "Bernd Berg"
    assert by_id["ID2"].fraction == "SPD" and by_id["ID2"].role == "Ministerin"  # from person.party
    assert by_id["ID0"].fraction == corpus.NO_FRACTION
    assert by_id["ID1"].agenda_title == "Mietpreisbremse verlängern" and by_id["ID1"].drucksachen == ["21/100"]


def test_short_title():
    st = corpus.short_title
    assert st(None, "Einzelplan 04") == "Haushalt: Bundeskanzler"
    assert st(None, "Einzelplan 14") == "Haushalt: Verteidigung"
    assert st(None, "Einzelplan 99") == "Haushalt: Einzelplan 99"
    assert st("(Schluss: 18:01 Uhr)", "Einzelplan 23") == "Einzelplan 23"
    assert st(None, "Einzelplan") == "Haushalt"
    assert st(None, "Zur Geschäftsordnung") == "Zur Geschäftsordnung"
    assert (
        st("Aktuelle Stunde | auf Verlangen der Fraktion der AfD | Angriffe in Erfurt", "Zusatzpunkt 1")
        == "Angriffe in Erfurt"
    )
    assert st("Vereinbarte Debatte: | 250 Jahre USA", "Tagesordnungspunkt 3") == "250 Jahre USA"
    gesetz = (
        "5 a) Erste Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur Änderung der StPO"
        " | b) Beratung des Antrags"
    )
    assert st(gesetz, "Tagesordnungspunkt 5") == "Zur Änderung der StPO"
    assert st("Befragung der Bundesregierung", "Tagesordnungspunkt 1") == "Befragung der Bundesregierung"
    zp = (
        "ZP 28 a) – Zweite und dritte Beratung des von der Bundesregierung eingebrachten Entwurfs eines Gesetzes zur X"
        " | – zu dem Antrag der Abgeordneten Y"
    )
    assert st(zp, "Zusatzpunkt 28, 29") == "Zur X"
