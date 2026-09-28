# Usage reference

All commands print exactly one JSON value to stdout. Errors go to stderr and
use exit code 2 for invalid input or 1 for an invalid index/I/O failure.

## Build

```console
local-evidence build SOURCE_DIR INDEX_DIR [--extensions .md .txt] [--chunk-lines N] [--overlap-lines N]
```

Only regular, readable UTF-8 files under `SOURCE_DIR` are indexed. Paths are
stored relative to that directory. The index is replaced atomically after a
successful build; a failed build does not destroy a prior valid index.

## Search

```console
local-evidence search INDEX_DIR "QUERY" [--top-k N] [--min-score FLOAT]
```

Results are ranked BM25 hits. Each includes `path`, 1-based `start_line` and
`end_line`, exact snapshot `text`, `source_sha256`, `score`, `rank`, and a
stable `chunk_id`. No answer is generated or paraphrased.

## Inspect and stale detection

```console
local-evidence inspect INDEX_DIR PATH --start-line N --end-line N
```

The command verifies the live file's SHA-256 before returning the requested
span. Edit or replace a source after indexing and the command reports a stale
source error; rebuild to intentionally accept the new snapshot.

## Stats

```console
local-evidence stats INDEX_DIR
```

Reports schema version, file/chunk/vocabulary counts, index bytes, and the
recorded tokenizer/BM25/chunk parameters.

## Reproducibility checklist

1. Keep the index directory with the source snapshot used for a review.
2. Record the JSON result's path, line range, and SHA-256.
3. If a file changes, preserve the old result and rebuild into a new index.
4. Run the benchmark locally for engineering measurements; do not present its
   synthetic results as a human productivity study.
