"""Assemble the map data for one week and render the static HTML pages."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from landscape.cluster import Clustering, majority, neighbours
from landscape.corpus import Speech

HERE = Path(__file__).parent


def week_payload(
    week: str, speeches: list[Speech], clustering: Clustering, vectors: np.ndarray, weeks: list[str]
) -> dict:
    agenda_of = majority([s.agenda_title for s in speeches], clustering.labels)
    clusters = [
        {"id": c, "terms": terms, "agenda": agenda_of[c], "n": int((clustering.labels == c).sum())}
        for c, terms in sorted(clustering.terms.items())
    ]
    order = sorted(speeches, key=lambda s: s.start)
    following = {s.id: next((o.id for o in order if o.start > s.end), None) for s in speeches}  # skips Zwischenfragen
    points = [
        {
            "id": s.id,
            "x": round(float(x), 3),
            "y": round(float(y), 3),
            "cluster": int(label),
            "speaker": s.speaker,
            "fraction": s.fraction,
            "role": s.role,
            "date": s.date,
            "agenda_id": s.agenda_item_id,
            "agenda": s.agenda_title,
            "top": s.top_id,
            "drucksachen": s.drucksachen,
            "chars": len(s.text),
            "comments": s.n_comments,
            "pdf": s.pdf_url,
            "cite": s.source_document_id,
            "similar": [speeches[j].id for j in near],
            "next": following[s.id],
            "paragraphs": s.paragraphs,
        }  # fmt: skip
        for s, (x, y), label, near in zip(speeches, clustering.xy, clustering.labels, neighbours(vectors), strict=True)
    ]
    linked = {k: v for s in speeches for k, v in s.linked.items()}  # Zwischenfragen too short to be points
    return {"week": week, "weeks": weeks, "clusters": clusters, "speeches": points, "linked": linked}


def _inline(template: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", r"<\/")
    return (HERE / template).read_text(encoding="utf-8").replace("__DATA__", data)


def render(payload: dict) -> str:
    return _inline("template.html", payload)


def render_index(summaries: list[dict]) -> str:
    """Landing page: one card per week, from `summary()` of each week payload."""
    return _inline("index.html", {"weeks": summaries})


def summary(payload: dict) -> dict:
    dates = sorted({s["date"] for s in payload["speeches"]})
    return {
        "week": payload["week"], "dates": dates, "speeches": len(payload["speeches"]),
        "clusters": [c["terms"][:3] for c in sorted(payload["clusters"], key=lambda c: -c["n"])],
    }  # fmt: skip
