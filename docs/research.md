# Research basis: local-evidence

## Primary paper and date

Renyi Qu, Ruixuan Tu, and Forrest Bao, **“Is Semantic Chunking Worth the Computational Cost?”**, arXiv:2410.13070, submitted 16 October 2024: <https://arxiv.org/abs/2410.13070>. The primary paper evaluates document retrieval, evidence retrieval, and retrieval-based answer generation, and reports that semantic chunking's computational costs are not justified by consistent gains (abstract and introduction). Its experiments compare fixed-size, breakpoint, and clustering chunkers; fixed-size is best on several tasks and differences are often minimal (Tables 1–2 and conclusion).

## Explicit method mapping

| Paper observation | Implementation decision | Deliberate omission |
|---|---|---|
| Fixed-size chunking is a strong, inexpensive baseline; semantic gains are inconsistent. | Deterministic fixed line windows with configurable overlap; benchmark against a substring scan and report retrieval metrics. | No claim that this reproduces the paper's embedding experiments or F1@5 numbers. |
| Evidence retrieval needs to preserve ground-truth evidence spans. | Every chunk records relative path plus exact 1-based start/end lines; `inspect` re-reads the source span. | No answer generation, semantic embeddings, or LLM reranking. |
| Paper studies long/stiched documents and warns chunking choices matter. | Chunk size/overlap are explicit index parameters recorded in metadata; benchmark varies only the frozen default unless an experiment adds a separate configuration. | No stitched BEIR/RAGBench data redistribution. |
| Retrieval quality must be measured rather than assumed. | Checked-in synthetic technical fixture with query relevance manifest; Recall@5, MRR@5, latency, build time, and index size. | Synthetic numbers are not external validity or user time-savings evidence. |

The product is therefore a useful offline evidence locator inspired by the paper's negative result: start with a cheap, inspectable baseline, expose citations, and make semantic complexity optional rather than silently required. It is not a reproduction and does not use the paper's code, data, model weights, or text.

## Rights and redistribution

The arXiv abstract page links to the paper's canonical record and PDF, but the record does not grant this implementation a license to redistribute paper text, datasets, or authors' code. This project redistributes neither paper text nor datasets. It implements an independent algorithm based on published ideas; the paper record should be rechecked for any author-supplied code/data license before using those materials, and patent status is not certified here. Original project code will be MIT-licensed. User-provided local documents remain user data and are never copied into the package or published. Fixture text is newly authored synthetic content. No model/API key is required.

## Competing tools and interoperability

- **ripgrep** (<https://github.com/BurntSushi/ripgrep>) is an excellent fast literal/regex scanner, but does not persist a BM25 ranked index or return chunk-level line citations as structured JSON.
- **SQLite FTS5** (<https://www.sqlite.org/fts5.html>) provides persistent local full-text search and BM25-like ranking; it is a natural alternative for larger corpora. This project remains dependency-free and stores a transparent JSON index for portability and inspectability.
- **Whoosh** (<https://whoosh.readthedocs.io/en/latest/>) is a Python search library with BM25 and indexing, but adds a dependency and is not required here.

These are comparison points, not claims of benchmark superiority. The implementation should document when to use them instead (large corpora, fuzzy/fielded search, or production concurrency).

## Evidence limits and reproducibility

The cited study's results are from its own datasets, embedding models, and evaluation protocol; they cannot be transferred to this tool. The local benchmark must print actual measured values and environment details. Any report of time saved must be a user study or a measured task-time comparison; absent that, state only retrieval latency and citation coverage. A benchmark pass is useful evidence that the tool works on its fixture, not proof of human productivity gains.

## Source links

1. Qu, Tu, Bao (2024), primary paper: <https://arxiv.org/abs/2410.13070> (paper HTML/PDF, date and methods).
2. SQLite FTS5 official documentation: <https://www.sqlite.org/fts5.html>.
3. ripgrep source repository and license: <https://github.com/BurntSushi/ripgrep>.
4. Whoosh documentation: <https://whoosh.readthedocs.io/en/latest/>.
