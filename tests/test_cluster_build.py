import json

import numpy as np

from landscape import build, corpus
from landscape.cluster import Clustering, cluster, cluster_terms, majority, neighbours


def test_cluster_terms_pick_distinctive_words():
    texts = ["wärmepumpe gas heizen kosten"] * 5 + ["kindergeld familien eltern kinder"] * 5
    labels = np.array([0] * 5 + [1] * 5)
    terms = cluster_terms(texts, labels, top=2)
    assert set(terms[0]) <= {"wärmepumpe", "gas", "heizen", "kosten"}
    assert set(terms[1]) <= {"kindergeld", "familien", "eltern", "kinder"}
    assert majority(["a", "a", "b", "c", "c", "c", "x", "x", "x", "x"], labels) == {0: "a", 1: "x"}


def test_neighbours_and_tiny_week_layout():
    v = np.array([[1, 0], [0.9, 0.1], [0, 1]], dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    assert neighbours(v, k=1) == [[1], [0], [1]]
    tiny = cluster(v, ["a", "b", "c"], min_cluster_size=8)  # too few speeches for UMAP/HDBSCAN
    assert tiny.xy.shape == (3, 2) and list(tiny.labels) == [-1, -1, -1] and tiny.terms == {}


def test_render_embeds_payload(conn):
    speeches = corpus.load_week(conn, "2026-W28")
    clustering = Clustering(xy=np.zeros((3, 2)), labels=np.array([0, 0, -1]), terms={0: ["miete", "wohnen"]})
    vectors = np.eye(3)
    payload = build.week_payload("2026-W28", speeches, clustering, vectors, ["2026-W28", "2026-W37"])
    assert payload["clusters"] == [
        {"id": 0, "terms": ["miete", "wohnen"], "agenda": "Befragung der Bundesregierung", "n": 2}
    ]
    p = payload["speeches"][1]
    assert p["comments"] == 1 and p["cluster"] == 0 and p["pdf"].endswith("21088.pdf") and len(p["similar"]) == 2
    html = build.render(payload)
    assert "__DATA__" not in html
    start = html.index("const DATA = ") + len("const DATA = ")
    assert json.loads(html[start : html.index(";\n", start)].replace("<\/", "</")) == json.loads(json.dumps(payload))
    index = build.render_index([build.summary(payload)])
    assert '"speeches": 3' in index and '"2026-07-08"' in index and "#tour=" in index
