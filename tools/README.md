# Tools

A small polyglot toolkit over the dataset in [`data/resources.json`](../data/resources.json).

Every tool answers the same questions in the same way:

| Command | What it does |
|---|---|
| `list` | List every resource |
| `search <query>` | Search name, description, tags, audience, category, region |
| `cat <category>` | Filter by `community`, `registry`, `treatment`, or `reference` |
| `stats` | Counts by category and region |
| `validate` | Check the dataset (unique ids, valid categories, http urls) |

The Python tool additionally offers `show <id>` and `export` (a flat TSV used by the C++ tool).

---

## Python — `tools/python/rare.py`

Reference implementation. Reads the JSON directly. No dependencies (standard library only).

```bash
python3 tools/python/rare.py validate
python3 tools/python/rare.py stats
python3 tools/python/rare.py cat registry
python3 tools/python/rare.py search aso
python3 tools/python/rare.py show n-lorem
python3 tools/python/rare.py export          # writes data/resources.tsv
```

## Go — `tools/go`

Standard library only (`encoding/json`).

```bash
go build -o rare ./tools/go
./rare list
./rare cat treatment
```

## Rust — `tools/rust`

Uses `serde` / `serde_json`.

```bash
cargo build --release --manifest-path tools/rust/Cargo.toml
./tools/rust/target/release/rare search aso
```

## C++ — `tools/cpp`

No third-party dependencies, so it reads the flat TSV export instead of parsing JSON.
Generate the export first:

```bash
python3 tools/python/rare.py export
make -C tools/cpp
./tools/cpp/rare stats
```

---

## Data path

All tools look for the dataset relative to the working directory and fall back through
`data/…`, `../../data/…`, `../../../data/…`. Override with an environment variable:

```bash
RARE_DATA=/path/to/resources.json python3 tools/python/rare.py list
```

---

## Verification status

Honesty matters more than a green checkmark here:

- **Python** — every command tested and passing.
- **Web page** (`index.html`) — JavaScript syntax-checked and the data path verified; not rendered in a real browser in the build environment.
- **Go, Rust, C++** — written to be correct and kept deliberately small and standard, but **not compiled** in the environment where this repository was generated (no Go/Rust/C++ toolchains were available there). Treat them as source to build locally; if you hit a compile error, please open an issue and it will be fixed.

## Contributing a tool

Adding another language is welcome — just implement the five commands above and read the
same dataset. Keep it dependency-light so it builds anywhere.
