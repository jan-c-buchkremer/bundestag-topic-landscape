# bundestag-topic-landscape

A topic landscape of one sitting week of the Bundestag: every speech of the week as a point on a
map, positioned by what it is about, coloured and filterable by fraction, speaker, agenda item and day.

Built on top of [bundestag-data-foundation](https://github.com/jan-c-buchkremer/bundestag-data-foundation),
whose SQLite store is read, never written.

```
speeches of one ISO week  →  multilingual-e5-base embeddings (cached)  →  UMAP + HDBSCAN  →  c-TF-IDF labels  →  one static HTML page
```

## Setup

Python 3.12+, [uv](https://docs.astral.sh/uv/). CPU only; no GPU, no Docker.

```sh
uv sync
export BDF_DB=/path/to/bundestag-data-foundation/data/bundestag.sqlite   # default: ../bundestag-data-foundation/data/bundestag.sqlite
uv run landscape weeks                 # sitting weeks in the store, with sitting numbers and speech counts
uv run landscape build 2026-W28        # → data/out/2026-W28.html
uv run landscape build --all           # every week plus data/out/index.html
uv run landscape serve                 # http://127.0.0.1:8000/ — re-renders pages from data/out/*.json on every request
```

The first build downloads the embedding model (~1.1 GB) into the Hugging Face cache and embeds the week
(about 6 minutes for ~400 speeches on a 2014 quad-core; faster on anything newer). Embeddings are cached in
`data/landscape.sqlite` by model and text hash, so rebuilding a week takes seconds and a model swap is a new
cache key. The whole Wahlperiode (31 weeks) took about three hours on that machine.

Open `data/out/index.html` in a browser, or run `landscape serve` while editing the template (Plotly.js and the
Inter font come from CDNs). Windows: `py -3.12 -m uv …`
works the same.

## Container

CI tests every push; pushes to `main` and `deploy` also publish `ghcr.io/jan-c-buchkremer/bundestag-topic-landscape`
(tags: branch name, short sha). The entrypoint is `landscape`, the working directory `/work`, so the defaults
write to `/work/data/out` and `/work/data/landscape.sqlite`. The foundation store is expected at
`/foundation/bundestag.sqlite` and the model cache at `/cache`:

```sh
docker run --rm -v "$BDF_DATA:/foundation" -v "$PWD/data:/work/data" -v "$PWD/hf-cache:/cache" \
  ghcr.io/jan-c-buchkremer/bundestag-topic-landscape:main build --all
```

Mount the foundation directory writable: the store is in WAL mode and SQLite creates a `-shm` file even for
read-only connections. The store is still opened with `mode=ro`.

## What the pages show

`index.html` lists every sitting week with its main topics, newest first. Each week page:

- One point per speech; position from UMAP on the speech embedding; topic colour and label from HDBSCAN + c-TF-IDF.
- Colour by topic, fraction, day, **agenda item** or role. Agenda-item colouring shows where one debate spreads
  across the landscape; each item takes the hue family of its sitting day, light for early items, deep for late ones.
- Filters as collapsible checkbox lists (fraction, day, agenda item, topic, speaker) with live counts: nothing
  checked means everything, OR within a list, AND across lists; ↻ re-sorts a list by frequency in the current view.
  The checkbox filters; a click on the name opens that value's card without filtering.
- Search: typing marks matches on the map, Enter turns the term into a saved filter (several terms are ANDed,
  each can be switched off or removed); matches are highlighted in the opened speech.
- Filtered-out speeches stay on the map at 10 % opacity ("Gefilterte abdunkeln", on by default) and point size
  follows speech length (on by default). „zurücksetzen“ restores all of that, the list order and the zoom.
- The view is kept in the URL, so it can be shared.
- Click a point: the full speech with interjections and applause inline, Zwischenfragen and Kurzinterventionen as
  cards where they were asked, citation and PDF link, the next speech in speaking order and the five most similar
  speeches of the week. Click a topic label or a name in a filter list: bar charts by fraction, day, topic, agenda
  item and speaker, with the speeches listed; every bar opens its own card.
- Regierungsbefragung turns are hidden by default (two-minute question/answer units under one agenda item); an
  explicit speaker or agenda filter shows them anyway.

## Touren

Three guided walkthroughs on the real data of a week, started from the **Tour** button in the header or
from the cards on the index page (`<week>.html#tour=woche|debatte|person`). Each step spotlights one
control and waits until you have done the action yourself: *Was war diese Woche los?* (map → topic → speech
→ source), *Eine Debatte über die Landschaft verfolgen* (dim mode, colour by TOP, tick a TOP, colour by
fraction) and *Einer Person folgen* (speaker list, profile, similar speeches by others, sharing the URL).

## How the corpus is cut

- A sitting week is the ISO week of the sitting date. No sitting week in WP 21 crosses a Sunday.
- Speeches split by the foundation at Zwischenfragen (`ID…`, `ID…-2`, …) are re-joined per speaker. Where another
  person spoke in between, the main speech gets a marker paragraph pointing to that person's speech (a
  Kurzintervention if the chair announced one, else a Zwischenfrage), and that speech a marker back. Questions
  under 500 characters are not points; their text is shipped with the page and opens in place.
- Speeches under 500 characters are dropped (procedural remarks, single questions).
- Ministers have no fraction in the protocol; their party from the master data is used instead. Non-MdB
  ministers and Länder representatives are shown as "ohne Fraktion".
- Speeches longer than the model window are embedded in paragraph-boundary chunks and mean-pooled.

Decisions and their reasons: `docs/decisions.md`. Data examination that preceded the design: `docs/examination.md`.

## Development

```sh
uv run pytest
uv run ruff check . && uv run ruff format .
```

Tests run against an in-memory copy of the foundation schema; no store, no model download needed.
