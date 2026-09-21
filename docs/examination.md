# Data examination (before design)

All numbers from `bundestag.sqlite` of the foundation on 2026-09-21, opened read-only.

## The store in one glance

| Wahlperiode 21, March 2025 – September 2026 | |
|---|---|
| sitting weeks | 31 (29 real ones; 2 are single ceremonial sittings) |
| sittings | 94 |
| agenda items | 933, of which 768 have speeches |
| speeches | 12,822 |
| speakers | 638 (624 MdBs, 14 non-MdBs) |
| text paragraphs | 130,054 |
| interjection/applause paragraphs | 90,321 |
| chair paragraphs | 28,845 |

| One typical week (2026-W28, 8–10 July) | |
|---|---|
| sittings | 3 (Wed, Thu, Fri) |
| agenda items with speeches | 29 |
| speeches | 476 → 412 after re-joining splits and dropping < 500 chars |
| of which Regierungsbefragung | 128 |
| speakers | 246 |

A typical speech is 10 text paragraphs of ~240 chars with 7 interjection/applause paragraphs interleaved.
Median speech length 2,900 chars ≈ 720 tokens; three quarters exceed the 512-token window of e5-base.

## What a speech is

- `speech.text` holds only the speaker's own paragraphs. Interjections and applause are `comment`
  paragraphs, presidency remarks are `chair` paragraphs; both stay attached to the speech. The `procedural`
  kind exists in the schema but is never produced.
- The presidency never appears as a speaker.
- One `rede` with a Zwischenfrage becomes several rows (`ID…`, `-2`, `-3`, … up to `-11`); the base
  speaker's answers are the odd parts. 1,207 suffixed rows, 483 same-speaker continuations.
- Fragestunde has no speech rows at all. Regierungsbefragung is fully present: 2,907 rows, median 606 chars.
- `speech.fraction` is NULL for every row with a `speaker_role` (1,883 rows): the Kanzler, ministers,
  Staatssekretäre. 1,590 of these are MdBs whose party is on `person`; 293 are non-MdBs without a party.
- `is_mdb = 0`: 4 federal ministers without a mandate (Hubig, Prien, Wildberger, Weimer), 8 Länder
  representatives, and 2 Nachrücker MdBs missing from the Stammdaten file.

## Attributes available

- per speech: order in sitting, sitting, agenda item, speaker, fraction/role, text, date, citation and PDF URL.
  No clock time, no page number.
- per paragraph: kind and text. Heckler name and fraction are inside the comment text, not parsed out.
- per speaker: party, gender, birth date, mandate type, constituency, state, committee memberships, Wikidata QID.
- per agenda item: `top_id`, long formal title (NULL for the 63 budget `Einzelplan` items), Drucksache numbers.
  Drucksache metadata itself is empty (DIP never fetched).

## Agenda titles as labels and ground truth

Titles are procedural boilerplate around the real title (`Beratung des Antrags der Abgeordneten … und der
Fraktion … | <title>`), average 437 chars, 138 items bundle several Drucksachen. A short-title rule (first
non-procedural `|` segment, or the law's name) works for the week examined.

Nearest-neighbour agreement with the agenda item on week 2026-W28 (436 speeches ≥ 500 chars, k = 5):
e5-base 0.60, TF-IDF 0.71 over all items; 0.72 vs 0.76 without Regierungsbefragung and Geschäftsordnung.
The merges e5 makes are thematic (Regierungserklärung ↔ economy Antrag ↔ Automobil Aktuelle Stunde).
Agenda items are therefore a sanity check, not a target.

## Embedding cost (i7-4790K, 4 cores, CPU only)

| model | window | throughput | one week | Wahlperiode |
|---|---|---|---|---|
| multilingual-e5-base, chunked | 512 | 4,000 chars/s | 6 min | ~2.5 h |
| bge-m3, whole speech | 2048 | 680 chars/s | 30 min | ~15 h |

## What would make the map misleading

1. Ministers without fraction — handled by the party fallback.
2. Regierungsbefragung — many topics under one item; hidden by default.
3. Split speeches as several points — re-joined.
4. Budget weeks — `Einzelplan` items without titles; labelled by ministry from `top_id`.
5. Point count is not speaking time; a 42,000-char Regierungserklärung is one point (size-by-length option).
6. Distances between clusters in 2-D UMAP mean nothing.
