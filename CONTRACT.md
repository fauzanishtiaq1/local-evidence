# local-evidence contract

## Product

`local-evidence` is an offline, local-first evidence finder for a directory of UTF-8 text/Markdown files. It builds a persistent lexical BM25 index over deterministic fixed-size, line-aware chunks and returns ranked excerpts with exact file paths and 1-based source line ranges. It never generates answers and never requires a model, network, or API key. Search citations refer to the immutable indexed snapshot, not an implicitly changing live file.

## Frozen Python API (`local_evidence.core`)

```python
from pathlib import Path
from typing import Iterable, Mapping, Sequence

def build_index(
    source_dir: str | Path,
    index_dir: str | Path,
    *,
    extensions: Sequence[str] = (".md", ".txt", ".rst"),
    chunk_lines: int = 40,
    overlap_lines: int = 5,
) -> dict:
    """Index readable files; return {files, chunks, vocabulary, index_dir}."""

def search_index(
    index_dir: str | Path,
    query: str,
    *,
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict]:
    """Return ranked hit dicts with rank, score, path, start_line, end_line,
    text, source_sha256, and chunk_id. Scores are deterministic BM25 scores."""

def inspect_document(
    index_dir: str | Path,
    path: str,
    *,
    start_line: int,
    end_line: int,
) -> dict:
    """Return the indexed snapshot span after verifying the current source
    SHA-256. Raise SourceChangedError if the live file differs."""

def index_stats(index_dir: str | Path) -> dict:
    """Return schema_version, files, chunks, vocabulary, bytes, and parameters."""
```

### Determinism, safety, and persistence

Tokenization is Unicode `casefold()` followed by contiguous runs of letters or digits (Unicode-aware), with punctuation treated as separators; no stop-word removal or stemming. BM25 is Robertson/Sparck Jones BM25 with `k1=1.2`, `b=0.75`, document length in tokens, and `idf=log(1 + (N-df+0.5)/(df+0.5))`. Scores sum query-term contributions (repeated query terms count once), then ties sort by normalized relative POSIX path, start line, and chunk ID. Metadata records tokenizer and BM25 parameters.

Schema version is an integer, currently `1`; loading rejects missing/unknown versions, non-finite or out-of-bound parameters, duplicate chunk IDs, invalid line ranges, invalid hashes, and malformed postings. Each indexed source stores UTF-8 snapshot text and its SHA-256 digest. `search_index` returns `source_sha256` and snippets from that snapshot. `inspect_document` verifies the current file's SHA-256 against the indexed digest and raises `SourceChangedError` rather than presenting stale live content; callers can still use search's explicit snapshot text.

Reject non-positive `chunk_lines`, negative `overlap_lines`, overlap >= chunk size, empty query, `top_k < 1`, paths escaping source_dir, symlinked files/directories that resolve outside source_dir, malformed or incompatible indexes, and undecodable files with actionable errors. If index_dir is inside source_dir, traversal skips the index subtree. Rebuilds occur in a sibling temporary directory and atomically replace the destination only after all files, hashes, and validation succeed; any failure leaves the prior valid index untouched. Source files are never modified.

## Frozen CLI

`python -m local_evidence build SOURCE_DIR INDEX_DIR [--extensions .md .txt] [--chunk-lines N] [--overlap-lines N]`

`python -m local_evidence search INDEX_DIR QUERY [--top-k N] [--min-score FLOAT]`

`python -m local_evidence inspect INDEX_DIR PATH --start-line N --end-line N`

`python -m local_evidence stats INDEX_DIR`

Every command prints one JSON object/array to stdout, diagnostics to stderr, and exits 0 on success, 2 on user/input errors, 1 on internal/index errors. `search` output is citation-ready: each result includes `path`, `start_line`, `end_line`, and `text`; snippets must not be fabricated or paraphrased.

## Evaluation fixed before implementation

The benchmark uses a checked-in synthetic but realistic fixture (technical notes with known relevant line ranges) and a deterministic query/relevance manifest. It reports Recall@5, MRR@5, build seconds, cold search median/p95 over 20 repetitions, index bytes, and a manual baseline: recursive filename-plus-substring scan that returns first matching files. The fixture is explicitly synthetic; results are not claims about human time saved or external corpora. A usefulness gate requires every query to produce a citation-bearing hit and comparison against the baseline. Limitations: lexical BM25 misses synonyms and cross-file inference; synthetic relevance labels do not establish generalization.
