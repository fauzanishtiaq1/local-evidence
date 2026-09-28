# local-evidence

Offline, local-first evidence search for UTF-8 Markdown and text files. Build a
small persistent BM25 index once, then retrieve ranked excerpts with exact
relative paths, 1-based line ranges, and a SHA-256 snapshot hash suitable for
review notes and citations. There is no model, network call, API key, answer
generation, or hidden data upload.

## Install

Python 3.10 or newer is required. The package has zero runtime dependencies.

```console
python -m pip install .
local-evidence --help
```

## Five-minute tutorial

From a directory containing `notes/meeting.md` and other UTF-8 text files:

```console
local-evidence build notes .local-evidence-index
local-evidence search .local-evidence-index "deployment rollback" --top-k 3
local-evidence inspect .local-evidence-index notes/meeting.md --start-line 12 --end-line 21
local-evidence stats .local-evidence-index
```

Search writes one JSON array to stdout. A result has this shape (values below
are illustrative field names, not measured output):

```json
[{"chunk_id":"notes/meeting.md:1-21","end_line":21,"path":"notes/meeting.md","rank":1,"score":1.23,"source_sha256":"...64 hex characters...","start_line":1,"text":"exact snapshot text"}]
```

Copy `path`, `start_line`, `end_line`, and `source_sha256` into a review record.
`inspect` reads the current file only after checking that its SHA-256 still
matches the indexed snapshot. If a source changed, it fails with a stale-source
error instead of silently presenting different evidence. Search results remain
the exact indexed snapshot, so a result is reproducible even after a source is
edited.

## How it works

The builder uses deterministic fixed-size, line-aware windows (40 lines with 5
lines of overlap by default), Unicode-aware tokenization, and transparent JSON
postings. Search uses BM25 with deterministic tie-breaking. Parameters and
source hashes are stored in the index. `--chunk-lines` and `--overlap-lines`
make the chunking choice explicit.

This is a practical lexical baseline inspired by the 2024 study *Is Semantic
Chunking Worth the Computational Cost?* (Qu, Tu, and Bao, arXiv:2410.13070).
It is not a reproduction of that paper: it does not ship its text, datasets,
code, embeddings, or model weights. See [`docs/research.md`](docs/research.md)
for the mapping and limitations.

## When to use something else

Use `ripgrep` for a one-off literal or regex scan, SQLite FTS5 for a larger
multi-user corpus, or an embedding/reranking system when synonym and semantic
matching are essential. This tool is intentionally offline, inspectable, and
easy to run in a restricted environment.

## Evidence and benchmark scope

The checked-in benchmark (when present in a checkout) uses newly authored
synthetic technical notes and reports Recall@5, MRR@5, build time, search
latency, and index size against a simple scan. Those measurements demonstrate
local functionality only; they are not a human time-savings study or a claim
of external-corpus generalization. Run `python benchmarks/run.py --output
benchmarks/results.json` to reproduce the local measurement.

## License

MIT. See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).
