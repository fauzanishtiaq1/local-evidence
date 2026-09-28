# Independent adversarial review

Date: 2026-09-28  
Scope: source, tests, packaging, documentation, benchmark, and fresh-user workflow.

## Evidence executed

- `python -m unittest discover -s tests -v`: **15 collected: 14 passed, 1 skipped**. The skip is
  `test_inspect_bounds_and_symlink_stale`, because symlink creation is unavailable in
  this Windows environment.
- `python scripts/check.py integration`: **3 passed; CHECK_OK**.
- `python benchmarks/run.py --output benchmarks/results-review.json`: **BENCHMARK_OK**;
  8/8 queries, citation exactness true, Recall@5 1.0, MRR@5 1.0, 160 fresh-process
  searches. The benchmark explicitly avoids comparing in-process baseline timing to
  process-level search timing.
- Fresh isolated venv outside the source tree: `pip install --no-deps .`, installed
  console script, copied `examples/` to a separate temp source, then built, searched,
  and inspected successfully. This confirms the wheel does not accidentally import
  the checkout.

## Adversarial checks

- Index loader recomputes document SHA-256, chunk text/line geometry, token lengths,
  postings, document frequency, average length, schema and BM25 parameters. Tampered
  chunk text, hashes, postings, numeric geometry, duplicate IDs, and malformed paths
  are covered by tests and reject as `InvalidIndexError`.
- Source traversal excludes an index nested below the source root and skips symlink directories while rejecting
  out-of-root symlink files. The positive symlink stale test could not run
  on this host; CI declares Windows and Linux, so CI remains the appropriate place to
  exercise the platform-specific branch.
- Atomic rebuild uses a sibling temporary directory and replaces only `index.json`
  after validating it; tests verify sentinels and failed rebuild preservation.
- Snapshot search returns indexed text and hash; `inspect` checks the live source hash
  and rejects edits. The two behaviors are documented distinctly.
- CLI configures UTF-8 output and rejects invalid query geometry, non-finite scores,
  malformed indexes, missing files, and invalid source input with documented exit codes.
- README/research claims are appropriately modest: the paper is cited as inspiration,
  no paper text/data/code is redistributed, and the synthetic benchmark is explicitly
  not a human time-savings or external-validity study.

## Findings

No release-blocking finding reproduced in this review. The only evidence limitation is
the unavailable Windows symlink test noted above; it is an honest environmental skip,
not evidence that the branch is correct on all filesystems.

## Recommendation

Release is supportable for the documented offline UTF-8 local-index use case, provided
the parent keeps the benchmark's timing caveat and synthetic-corpus limitation in the
public claims. Do not describe the results as measured human productivity or a speedup.
