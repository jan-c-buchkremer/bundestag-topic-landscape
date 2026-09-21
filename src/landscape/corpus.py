"""Read one sitting week of speeches from the foundation store (read-only)."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

MIN_CHARS = 500  # shorter units are procedural remarks and single questions, see docs/decisions.md

# speech.fraction is NULL for ministers; person.party fills the gap
PARTY_TO_FRACTION = {"CDU": "CDU/CSU", "CSU": "CDU/CSU", "DIE LINKE.": "Die Linke"}
NO_FRACTION = "ohne Fraktion"  # non-MdB ministers, Länder ministers

EINZELPLAN = {
    "1": "Bundespräsident", "2": "Bundestag", "3": "Bundesrat", "4": "Bundeskanzler", "5": "Auswärtiges Amt",
    "6": "Inneres", "7": "Justiz", "8": "Finanzen", "9": "Wirtschaft und Energie", "10": "Landwirtschaft",
    "11": "Arbeit und Soziales", "12": "Verkehr", "14": "Verteidigung", "15": "Gesundheit", "16": "Umwelt",
    "17": "Bildung, Familie", "19": "Bundesverfassungsgericht", "20": "Bundesrechnungshof",
    "23": "Entwicklung", "24": "Digitales", "25": "Wohnen, Bau", "30": "Forschung", "32": "Bundesschuld",
    "60": "Allgemeine Finanzverwaltung",
}  # fmt: skip

_PROCEDURAL = re.compile(
    r"^((\d+|[a-z]\)|–|ZP\s*\d+)\s*)*"
    r"(Erste|Zweite|Dritte|Beratung|Abgabe|auf Verlangen|Aktuelle Stunde|Wahlvorschl|Vereinbarte Debatte:|"
    r"Beschlussempfehlung|Bericht des|Antrag der|zu dem Antrag|zu der|\(Schluss)",
)
_GESETZ = re.compile(r"^.*?Entwurfs eines (\w+ )?Gesetzes ")


def connect() -> sqlite3.Connection:
    path = Path(os.environ.get("BDF_DB", "../bundestag-data-foundation/data/bundestag.sqlite"))
    if not path.exists():
        raise FileNotFoundError(f"foundation store not found: {path} (set BDF_DB)")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def week_id(date: str) -> str:
    y, w, _ = dt.date.fromisoformat(date).isocalendar()
    return f"{y}-W{w:02d}"


def week_range(week: str) -> tuple[str, str]:
    y, w = int(week[:4]), int(week[6:])
    monday = dt.date.fromisocalendar(y, w, 1)
    return monday.isoformat(), (monday + dt.timedelta(days=6)).isoformat()


def weeks(conn: sqlite3.Connection) -> list[dict]:
    """Every ISO week with sittings: id, sitting numbers, speech count."""
    out: dict[str, dict] = {}
    for r in conn.execute(
        "SELECT st.date, st.number, COUNT(s.id) n FROM sitting st LEFT JOIN speech s ON s.sitting_id = st.id "
        "GROUP BY st.id ORDER BY st.date"
    ):
        wid = week_id(r["date"])
        w = out.setdefault(wid, {"week": wid, "sittings": [], "speeches": 0})
        w["sittings"].append(r["number"])
        w["speeches"] += r["n"]
    return list(out.values())


def short_title(title: str | None, top_id: str) -> str:
    """A label-sized title: the first non-procedural segment, or the law's name."""
    if not title:
        if top_id.startswith("Einzelplan"):
            num = top_id.removeprefix("Einzelplan").strip().lstrip("0")
            return f"Haushalt: {EINZELPLAN.get(num, top_id)}" if num else "Haushalt"
        return top_id
    segments = [s.strip() for s in title.split("|") if not s.strip().startswith("(Schluss")]
    if not segments:
        return top_id
    for s in segments:
        if not _PROCEDURAL.match(s):
            return s
    s = _GESETZ.sub("", segments[0])
    return s[0].upper() + s[1:]


@dataclass
class Speech:
    id: str
    date: str
    person_id: str
    speaker: str
    fraction: str
    role: str | None
    top_id: str
    agenda_item_id: str
    agenda_title: str
    drucksachen: list[str]
    text: str
    pdf_url: str
    source_document_id: str
    part_ids: list[str]
    paragraphs: list[tuple[str, str]] = field(default_factory=list)  # (kind, text) incl. interjections

    @property
    def n_comments(self) -> int:
        return sum(k == "comment" for k, _ in self.paragraphs)


_SQL = """
SELECT s.id, st.date, s.person_id, s.speaker_name, s.fraction, s.speaker_role, s.text, s.source_document_id,
       st.pdf_url, p.party, a.id AS agenda_item_id, a.top_id, a.title AS agenda_title, a.drucksache_numbers
FROM speech s
JOIN sitting st ON st.id = s.sitting_id
JOIN person p ON p.id = s.person_id
LEFT JOIN agenda_item a ON a.id = s.agenda_item_id
WHERE st.date BETWEEN ? AND ?
ORDER BY st.date, s.position
"""

_SQL_PARAGRAPHS = """
SELECT sp.speech_id, sp.kind, sp.text
FROM speech_paragraph sp JOIN speech s ON s.id = sp.speech_id JOIN sitting st ON st.id = s.sitting_id
WHERE st.date BETWEEN ? AND ?
ORDER BY sp.position
"""


def load_week(conn: sqlite3.Connection, week: str) -> list[Speech]:
    """Speeches of one week with split parts re-joined and short units dropped."""
    span = week_range(week)
    speeches: list[Speech] = []
    by_base: dict[tuple[str, str], Speech] = {}  # (rede base id, person) -> first part
    for r in conn.execute(_SQL, span):
        base = re.sub(r"-\d+$", "", r["id"])
        head = by_base.get((base, r["person_id"]))
        if head is not None:
            head.text += "\n\n" + r["text"]
            head.part_ids.append(r["id"])
            continue
        sp = Speech(
            id=r["id"], date=r["date"], person_id=r["person_id"],
            speaker=r["speaker_name"].split(",")[0].split(" (")[0],
            fraction=r["fraction"] or PARTY_TO_FRACTION.get(r["party"], r["party"] or NO_FRACTION),
            role=r["speaker_role"], top_id=r["top_id"], agenda_item_id=r["agenda_item_id"],
            agenda_title=short_title(r["agenda_title"], r["top_id"]),
            drucksachen=json.loads(r["drucksache_numbers"]), text=r["text"], pdf_url=r["pdf_url"],
            source_document_id=r["source_document_id"], part_ids=[r["id"]],
        )  # fmt: skip
        by_base[(base, r["person_id"])] = sp
        speeches.append(sp)
    speeches = [s for s in speeches if len(s.text) >= MIN_CHARS]

    by_part: dict[str, list[tuple[str, str]]] = {pid: [] for s in speeches for pid in s.part_ids}
    for r in conn.execute(_SQL_PARAGRAPHS, span):
        if r["speech_id"] in by_part:
            by_part[r["speech_id"]].append((r["kind"], r["text"]))
    for s in speeches:
        for pid in s.part_ids:
            s.paragraphs.extend(by_part[pid])
    return speeches
