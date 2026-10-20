#!/usr/bin/env python3
"""rare.py - reference CLI for the n-of-1-resources dataset.

Reads data/resources.json (the single source of truth) and offers search,
filtering, stats, validation and a flat TSV export for the dependency-free
tools in this repository.

Usage:
    python3 rare.py list
    python3 rare.py search <query>
    python3 rare.py cat <category>          # community|registry|treatment|reference
    python3 rare.py show <id>
    python3 rare.py stats
    python3 rare.py validate
    python3 rare.py export [path]           # writes a flat TSV

Options:
    --data PATH   path to resources.json (default: auto-located in the repo)
    --json        emit JSON instead of human-readable text
"""

from __future__ import annotations

import json
import os
import sys

VALID_CATEGORIES = ("community", "registry", "treatment", "reference")


def default_data_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(repo_root, "data", "resources.json")


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def match(r: dict, query: str) -> bool:
    q = query.lower()
    haystack = " ".join(
        [
            r.get("name", ""),
            r.get("description", ""),
            " ".join(r.get("tags", []) or []),
            " ".join(r.get("audience", []) or []),
            r.get("category", ""),
            r.get("region", ""),
        ]
    ).lower()
    return q in haystack


def fmt_row(r: dict) -> str:
    return f"[{r.get('category','?'):9}] {r.get('name','?'):<44} {r.get('url','')}"


def cmd_list(rows, as_json):
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    for r in rows:
        print(fmt_row(r))
    print(f"\n{len(rows)} resource(s)")
    return 0


def cmd_show(rows, target, as_json):
    for r in rows:
        if r.get("id") == target:
            if as_json:
                print(json.dumps(r, indent=2, ensure_ascii=False))
            else:
                print(f"{r.get('name')}\n{'=' * len(r.get('name',''))}")
                print(f"id:       {r.get('id')}")
                print(f"category: {r.get('category')}")
                print(f"region:   {r.get('region')}")
                print(f"audience: {', '.join(r.get('audience', []) or [])}")
                print(f"url:      {r.get('url')}")
                print(f"tags:     {', '.join(r.get('tags', []) or [])}")
                print(f"\n{r.get('description','')}")
            return 0
    print(f"no resource with id '{target}'", file=sys.stderr)
    return 1


def cmd_stats(rows, as_json):
    cats, regions = {}, {}
    for r in rows:
        cats[r.get("category", "?")] = cats.get(r.get("category", "?"), 0) + 1
        regions[r.get("region", "?")] = regions.get(r.get("region", "?"), 0) + 1
    if as_json:
        print(json.dumps({"total": len(rows), "by_category": cats, "by_region": regions}, indent=2))
        return 0
    print(f"total: {len(rows)}")
    print("\nby category:")
    for k in VALID_CATEGORIES:
        if k in cats:
            print(f"  {k:10} {cats[k]}")
    print("\nby region:")
    for k in sorted(regions):
        print(f"  {k:10} {regions[k]}")
    return 0


def cmd_validate(rows) -> int:
    problems = []
    seen = set()
    for i, r in enumerate(rows):
        rid = r.get("id")
        if not rid:
            problems.append(f"row {i}: missing id")
        elif rid in seen:
            problems.append(f"row {i}: duplicate id '{rid}'")
        else:
            seen.add(rid)
        if r.get("category") not in VALID_CATEGORIES:
            problems.append(f"{rid}: invalid category '{r.get('category')}'")
        if not str(r.get("url", "")).startswith("http"):
            problems.append(f"{rid}: url does not start with http")
        for field in ("name", "description", "region"):
            if not r.get(field):
                problems.append(f"{rid}: missing {field}")
        if not isinstance(r.get("tags", []), list):
            problems.append(f"{rid}: tags must be a list")
        if not isinstance(r.get("audience", []), list):
            problems.append(f"{rid}: audience must be a list")
    if problems:
        print(f"INVALID - {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"OK - {len(rows)} resources, all ids unique, categories/urls valid")
    return 0


def cmd_export(rows, path: str) -> int:
    cols = ["id", "name", "category", "region", "url", "audience", "tags", "description"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            line = [
                str(r.get("id", "")),
                str(r.get("name", "")),
                str(r.get("category", "")),
                str(r.get("region", "")),
                str(r.get("url", "")),
                ",".join(r.get("audience", []) or []),
                ",".join(r.get("tags", []) or []),
                str(r.get("description", "")).replace("\t", " ").replace("\n", " "),
            ]
            fh.write("\t".join(line) + "\n")
    print(f"wrote {len(rows)} rows to {path}")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--json"]
    as_json = "--json" in argv
    data_path = default_data_path()

    if "--data" in args:
        i = args.index("--data")
        if i + 1 >= len(args):
            print("--data needs a path", file=sys.stderr)
            return 2
        data_path = args[i + 1]
        del args[i : i + 2]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    try:
        doc = load(data_path)
    except FileNotFoundError:
        print(f"data file not found: {data_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {data_path}: {exc}", file=sys.stderr)
        return 1

    rows = doc.get("resources", [])
    cmd = args[0]

    if cmd == "list":
        return cmd_list(rows, as_json)
    if cmd == "search":
        if len(args) < 2:
            print("search needs a query", file=sys.stderr)
            return 2
        return cmd_list([r for r in rows if match(r, " ".join(args[1:]))], as_json)
    if cmd == "cat":
        if len(args) < 2:
            print(f"cat needs one of: {', '.join(VALID_CATEGORIES)}", file=sys.stderr)
            return 2
        cat = args[1].lower()
        if cat not in VALID_CATEGORIES:
            print(f"unknown category '{cat}'; expected one of {', '.join(VALID_CATEGORIES)}", file=sys.stderr)
            return 2
        return cmd_list([r for r in rows if r.get("category") == cat], as_json)
    if cmd == "show":
        if len(args) < 2:
            print("show needs an id", file=sys.stderr)
            return 2
        return cmd_show(rows, args[1], as_json)
    if cmd == "stats":
        return cmd_stats(rows, as_json)
    if cmd == "validate":
        return cmd_validate(rows)
    if cmd == "export":
        out = args[1] if len(args) > 1 else os.path.join(os.path.dirname(data_path), "resources.tsv")
        return cmd_export(rows, out)

    print(f"unknown command '{cmd}'", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
