"""landscape weeks | landscape build 2026-W28 [2026-W26 …] | landscape build --all | landscape serve"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from landscape import build, corpus, embed


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="landscape")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("weeks", help="list sitting weeks in the foundation store")
    b = sub.add_parser("build", help="build the map for one or more weeks")
    b.add_argument("weeks", nargs="*", help="ISO weeks, e.g. 2026-W28")
    b.add_argument("--all", action="store_true", help="every week in the store, plus the index page")
    b.add_argument("--out", type=Path, default=Path("data/out"))
    b.add_argument("--store", type=Path, default=Path("data/landscape.sqlite"), help="embedding cache")
    b.add_argument("--min-cluster-size", type=int, default=8)
    sv = sub.add_parser("serve", help="dev server: pages are re-rendered from data/out/*.json on every request")
    sv.add_argument("--out", type=Path, default=Path("data/out"))
    sv.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    if args.cmd == "serve":
        from landscape.serve import serve

        serve(args.out, args.port)
        return

    conn = corpus.connect()
    all_weeks = corpus.weeks(conn)
    if args.cmd == "weeks":
        for w in all_weeks:
            first, last, n = w["sittings"][0], w["sittings"][-1], len(w["sittings"])
            print(f"{w['week']}  sittings {first}-{last} ({n})  speeches {w['speeches']}")
        return

    from landscape.cluster import cluster

    week_ids = [w["week"] for w in all_weeks]
    targets = week_ids if args.all else args.weeks
    if not targets:
        sys.exit("give at least one week or --all; see `landscape weeks`")
    store = embed.open_store(args.store)
    args.out.mkdir(parents=True, exist_ok=True)
    summaries = []
    for week in targets:
        speeches = corpus.load_week(conn, week)
        if not speeches:
            print(f"{week}: no speeches, skipped")
            continue
        print(f"{week}: {len(speeches)} speeches after re-joining splits and dropping < {corpus.MIN_CHARS} chars")
        vectors = embed.embed_speeches(speeches, store)
        result = cluster(vectors, [s.text for s in speeches], args.min_cluster_size)
        payload = build.week_payload(week, speeches, result, vectors, week_ids)
        noise = sum(s["cluster"] < 0 for s in payload["speeches"])
        print(f"  {len(payload['clusters'])} clusters, {noise} unclustered speeches")
        for c in payload["clusters"]:
            print(f"  {c['id']:2} ({c['n']:3}) {', '.join(c['terms'])}")
        (args.out / f"{week}.html").write_text(build.render(payload), encoding="utf-8")
        (args.out / f"{week}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        summaries.append(build.summary(payload))
    if args.all:
        (args.out / "index.html").write_text(build.render_index(summaries), encoding="utf-8")
    print(f"wrote {len(summaries)} week page(s) to {args.out}")


if __name__ == "__main__":
    main()
