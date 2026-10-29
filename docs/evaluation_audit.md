# RepoPilot evaluation dataset audit

## Scope and provenance

This audit was performed against the clean `main` checkout at
`8645ac8fd28ba14365a0e61269bee015eb3db778` on 2026-10-30. The audit covers
all 15 cases in `evals/datasets/ground_truth.json` and all 41 cases in
`evals/datasets/ground_truth_multirepo.json`.

The RepoPilot cases refer to source revisions `52e2e6b212405087fc79fd46ec3bb0edee5dc952`,
`773b4de9ddc72f611763cb642c25ba2ea9e7b4dc`, and
`8f9a8c92385c1fd23156f0e5fa32bf7673842574`, plus the current audited
revision `8645ac8fd28ba14365a0e61269bee015eb3db778`; each is a local Git
commit.
The three external repositories are represented by checked-in `snapshot.json`
metadata and their recorded full revisions:

| Repository | Recorded revision | Verification boundary |
|---|---|---|
| DataPulse-Analytics | `d2e80f7e737823bd349de76b421cdbf7d3a352d1` | Matches `evals/corpora/datapulse/snapshot.json`; source files are not Git objects in this checkout. |
| HealthStream-ETL | `c276139ca273be09c6f177b4a25b420766cade16` | Matches `evals/corpora/healthstream/snapshot.json`; source files are not Git objects in this checkout. |
| low-latency-matching-engine | `fdda1c07e75f7ab87b33a74a60a5eb04e99ac7b1` | Matches `evals/corpora/matching-engine/snapshot.json`; source files are not Git objects in this checkout. |

The RepoPilot multirepository entry is materialized from its recorded full Git
revision with `git archive`; the supplied checkout is used only as the local
Git object store. Repeatability therefore requires that the recorded revision
be present. The explicit `--use-checkout` option is reserved for checkout-
relative proposed-change testing.

`PASS` means the case was verified as authored. `CORRECT` means a confirmed
dataset defect was corrected and the case was reverified. `AMBIGUOUS` means
the available corpus does not make the intended test unambiguous. `FAIL`
means the expected evidence is wrong or absent. No case is marked `PASS`
solely because the retrieval evaluator returned a result.

## Single-repository dataset

| Case ID | Source revision | Expected path/range | Expected fact | Evidence inspected | Verdict | Reason / recommendation |
|---|---|---|---|---|---|---|
| ground-truth-001 | `52e2e6b...` | `src/repopilot/api.py:26-38` | Bearer-token middleware protects API routes. | `require_api_token`; parses bearer header and compares configured token. | PASS | Direct support; query targets the symbol. |
| ground-truth-002 | `52e2e6b...` | `src/repopilot/indexer.py:187-257` | Indexing uses known hashes and parser metadata for incremental indexing. | `index_repository`; known hashes, parser version, and file metadata are used. | PASS | Direct support; range and symbol are valid. |
| ground-truth-003 | `52e2e6b...` | `src/repopilot/store.py:282-331` | Search applies query clauses and optional path-prefix constraints. | `search`; query clauses and prefix predicates are constructed. | PASS | Direct support. |
| ground-truth-005 | `52e2e6b...` | `src/repopilot/llm.py:19-38` | Provider URL validation rejects malformed or unsafe base URLs. | `_provider_url`; validates scheme, hostname, auth, query, and port conditions. | PASS | Direct support. |
| ground-truth-006 | `773b4de...` | `src/repopilot/security.py:123-131` | Repository root validation requires an existing directory with a repository marker. | `safe_repository_root`; resolves the path, checks directory existence, and checks repository markers. | CORRECT | Original fact overclaimed traversal prevention; corrected to the behavior actually implemented and reverified. |
| ground-truth-007 | `8645ac8...` | `src/repopilot/security.py:238-330` | Safe file reads use handle-based checks and no-follow semantics. | `read_safe_text`; descriptor-based checks and `O_NOFOLLOW`/Windows handle logic. | CORRECT | The prior `8f9a8c...` provenance did not match its 236-328 source range; provenance now matches the current audited checkout. |
| ground-truth-008 | `52e2e6b...` | `src/repopilot/indexer.py:43-102` | Python parsing extracts qualified names and readable signatures. | `parse_python`; AST traversal emits qualified symbols and signatures. | PASS | Direct support. |
| ground-truth-009 | `52e2e6b...` | `src/repopilot/indexer.py:105-184` | Import extraction uses language-specific static parsing rules. | `extract_imports`; Python, JavaScript/TypeScript, and other language rules. | PASS | Direct support. |
| ground-truth-010 | `52e2e6b...` | `src/repopilot/store.py:333-360` | Fallback retrieval keeps snippets bounded and query-relevant. | `_fallback_search`; bounds content to 500 characters and requires query terms. | PASS | Direct support. |
| ground-truth-011 | `52e2e6b...` | `src/repopilot/store.py:404-421` | Memory creation persists kind, summary, and evidence. | `create_memory`; inserts requested fields into persistent storage. | PASS | Direct support. |
| ground-truth-012 | `52e2e6b...` | `src/repopilot/llm.py:41-168` | Grounded answer generation validates provider output and supported citations. | `generate_grounded_answer`; validates response shape and citations against evidence. | PASS | Direct support. |
| ground-truth-013 | `52e2e6b...` | `src/repopilot/api.py:141-231` | Ask selects query-matched evidence and abstains when support is unavailable. | `ask_repository`; filters evidence and returns an abstention path. | PASS | Direct support. |
| ground-truth-014 | `52e2e6b...` | `src/repopilot/store.py:459-466` | Repository deletion removes persisted repository state. | `delete_repository`; removes file-search and repository records. | PASS | Direct support. |
| ground-truth-015 | `52e2e6b...` | no expected source | No repository evidence supports the query. | Literal query terms were absent from the sanitized source corpus. | PASS | Clean unsupported-query control. |
| ground-truth-016 | `52e2e6b...` | no expected source | No repository evidence supports the query. | Literal query terms were absent from the sanitized source corpus. | PASS | Clean unsupported-query control. |

The omitted numeric case `ground-truth-004` is a dataset numbering gap, not a
missing evaluation record. It should be renumbered only as a deliberate dataset
versioning change, not silently inferred by the evaluator.

## Multirepository dataset

| Case ID | Source revision | Expected path/range | Expected fact | Evidence inspected | Verdict | Reason / recommendation |
|---|---|---|---|---|---|---|
| ground-truth-001 | `8f9a8c9...` | `src/repopilot/api.py:26-38` | Bearer-token middleware protects API routes. | Same RepoPilot source and symbol as single-repository case 001. | PASS | Direct support; intentional cross-evaluator overlap. |
| ground-truth-002 | `8f9a8c9...` | `src/repopilot/indexer.py:187-257` | Incremental indexing uses hashes and parser metadata. | `index_repository` implementation. | PASS | Direct support. |
| ground-truth-003 | `8f9a8c9...` | `src/repopilot/store.py:282-331` | Search applies clauses and path-prefix constraints. | `search` implementation. | PASS | Direct support. |
| ground-truth-005 | `8f9a8c9...` | `src/repopilot/llm.py:19-38` | Provider URL validation rejects unsafe URLs. | `_provider_url` implementation. | PASS | Direct support. |
| ground-truth-006 | `8f9a8c9...` | `src/repopilot/security.py:123-131` | Repository roots require a valid existing repository directory. | `safe_repository_root`. | PASS | Direct support; wording is narrower than the corrected single-repository fact but accurate. |
| ground-truth-007 | `8f9a8c9...` | `src/repopilot/security.py:236-328` | Safe reads use descriptor/no-follow protections. | `read_safe_text`. | CORRECT | The pinned revision uses 236-328; the prior range was from the newer checkout. |
| ground-truth-008 | `8f9a8c9...` | `src/repopilot/indexer.py:43-102` | Python parsing extracts qualified names and signatures. | `parse_python`. | PASS | Direct support. |
| ground-truth-009 | `8f9a8c9...` | `src/repopilot/indexer.py:105-184` | Imports use language-specific static parsing. | `extract_imports`. | PASS | Direct support. |
| ground-truth-010 | `8f9a8c9...` | `src/repopilot/store.py:333-360` | Fallback retrieval is bounded and query-relevant. | `_fallback_search`. | PASS | Direct support. |
| ground-truth-011 | `8f9a8c9...` | `src/repopilot/store.py:404-421` | Memory creation persists requested fields. | `create_memory`. | PASS | Direct support. |
| ground-truth-012 | `8f9a8c9...` | `src/repopilot/llm.py:41-168` | Grounded answers validate output and citations. | `generate_grounded_answer`. | PASS | Direct support. |
| ground-truth-013 | `8f9a8c9...` | `src/repopilot/api.py:141-231` | Ask selects matched evidence and abstains without support. | `ask_repository`. | PASS | Direct support. |
| ground-truth-014 | `8f9a8c9...` | `src/repopilot/store.py:459-466` | Deletion removes persisted repository state. | `delete_repository`. | PASS | Direct support. |
| ground-truth-015 | `8f9a8c9...` | no expected source | No repository evidence supports the query. | `quux zxqvpl` had no source-term hits. | PASS | Clean unsupported-query control. |
| ground-truth-016 | `8f9a8c9...` | no expected source | No repository evidence supports the query. | `flarn zybberwock` had no source-term hits. | PASS | Clean unsupported-query control. |
| multirepo-positive-001 | `d2e80f7...` | `backend/app/main.py:33` | API key authentication uses constant-time comparison. | `compare_digest` after expected-key lookup. | PASS | Direct support in pinned snapshot metadata. |
| multirepo-positive-002 | `d2e80f7...` | `backend/app/main.py:67` | Database readiness executes a lightweight query. | `db.execute(select(1))`. | PASS | Direct support. |
| multirepo-positive-003 | `d2e80f7...` | `backend/app/main.py:91` | Revenue metrics use a null-safe aggregate. | `coalesce(sum(...), 0)`. | PASS | Direct support. |
| multirepo-positive-004 | `d2e80f7...` | `backend/app/main.py:100` | Top event counts have deterministic tie ordering. | Count descending and name ascending ordering. | PASS | Direct support. |
| multirepo-positive-005 | `d2e80f7...` | `backend/app/schemas.py:25` | Event input forbids undeclared fields. | `ConfigDict(extra="forbid")`. | PASS | Direct support. |
| multirepo-positive-006 | `d2e80f7...` | `backend/app/models.py:11` | Event model defines a composite time/event index. | Composite index declaration. | PASS | Direct support. |
| multirepo-positive-007 | `c276139...` | `healthstream_etl.py:14-24` | ETL requires declared input columns. | `REQUIRED_COLUMNS` plus `_normalize` rejects rows missing any required column. | PASS | Range now includes the required-column list and its enforcement. |
| multirepo-positive-008 | `c276139...` | `healthstream_etl.py:42` | ETL rejects noncanonical ISO dates. | Date normalization and `isoformat`. | PASS | Direct support. |
| multirepo-positive-009 | `c276139...` | `healthstream_etl.py:50` | ETL rejects negative or nonfinite Decimal amounts. | Finiteness and negative-value checks. | PASS | Direct support. |
| multirepo-positive-010 | `c276139...` | `healthstream_etl.py:104` | ETL detects duplicate event identifiers. | `seen_ids` duplicate check. | PASS | Direct support. |
| multirepo-positive-011 | `c276139...` | `healthstream_etl.py:88` | ETL rejects duplicate CSV header names. | Duplicate-header validation. | PASS | Direct support. |
| multirepo-positive-012 | `c276139...` | `healthstream_etl.py:121-123` | Daily summaries aggregate by date and encounter type. | Grouping key plus encounter-count and amount accumulation. | PASS | Range includes both grouping and aggregation operations. |
| multirepo-positive-013 | `fdda1c0...` | `src/OrderBook.cpp:12` | Order insertion rejects invalid prices, zero quantities, and duplicate IDs. | Validation branch at line 12. | PASS | Direct support. |
| multirepo-positive-014 | `fdda1c0...` | `src/OrderBook.cpp:36` | Buy orders cross when their limit reaches the resting ask. | Buy-side price comparison. | PASS | Direct support. |
| multirepo-positive-015 | `fdda1c0...` | `src/OrderBook.cpp:16-22` | Accepted orders are stored and placed on the appropriate price-level queue. | `orders_.emplace`, side-specific queue insertion, and queue position. | CORRECT | Original case duplicated positive-013 at line 12; query, range, category, and fact were changed to test distinct insertion behavior. |
| multirepo-positive-016 | `fdda1c0...` | `src/OrderBook.cpp:115` | Matching executes the smaller remaining quantity. | `std::min(remaining, resting->remaining)`. | PASS | Direct support. |
| multirepo-positive-017 | `fdda1c0...` | `src/OrderBook.cpp:152-153` | Empty bid books use a minimum-price sentinel. | Empty-bid branch and `numeric_limits<Price>::min()`. | PASS | Range includes the sentinel value, not only the conditional. |
| multirepo-positive-018 | `fdda1c0...` | `src/OrderPool.cpp:22-23` | Order pool allocates more storage when the free list is empty. | Empty free-list condition and `make_unique<Order>()` allocation. | PASS | Range includes the allocation action. |
| multirepo-negative-001 | `8f9a8c9...` | no expected source | No repository evidence supports the query. | `tesseract qelvorn` has no source-term hits. | CORRECT | Original query used common words that produced lexical overlap; replaced with a verified no-hit control. |
| multirepo-negative-002 | `8f9a8c9...` | no expected source | No repository evidence supports the query. | `mavrix zundel` has no source-term hits. | CORRECT | Original query used common words that produced lexical overlap; replaced with a verified no-hit control. |
| multirepo-negative-003 | `d2e80f7...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in DataPulse snapshot. | PASS | Clean unsupported-query control. |
| multirepo-negative-004 | `d2e80f7...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in DataPulse snapshot. | PASS | Clean unsupported-query control. |
| multirepo-negative-005 | `c276139...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in HealthStream snapshot. | PASS | Clean unsupported-query control. |
| multirepo-negative-006 | `c276139...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in HealthStream snapshot. | PASS | Clean unsupported-query control. |
| multirepo-negative-007 | `fdda1c0...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in matching snapshot. | PASS | Clean unsupported-query control. |
| multirepo-negative-008 | `fdda1c0...` | no expected source | No repository evidence supports the query. | No literal or component-term hits in matching snapshot. | PASS | Clean unsupported-query control. |

## Integrity and evaluation controls

- The single-repository and provider evaluators materialize each question's
  recorded full `source_revision` with `git archive`; missing revisions fail
  closed. Materialized snapshots exclude ground-truth datasets, audit reports,
  external fixture corpora, and generated evaluation artifacts. The multirepo
  evaluator uses the same materializer for its pinned RepoPilot revision.
  Regression tests cover revision pinning and exclusions.
- Cross-dataset overlap is intentional: the RepoPilot cases are reused to
  exercise both evaluators. It must not be described as an independent second
  corpus or independent review.
- The only confirmed duplicate positive was multirepo-positive-013 and
  multirepo-positive-015; the latter is now a distinct order-storage case.
- Line ranges were checked against the cited source snapshots. External source
  files are not present in this checkout beyond their snapshot metadata, so the
  external line review is bounded by the source snapshot material available
  during authoring; it is not a fresh remote checkout verification.

## Commands and results

The following commands were run after the corrections. The multirepository
runner materializes the external source files from the embedded `snapshot.json`
bundles before indexing them.

```text
PYTHONPATH=src python evals/run_ground_truth.py --root .
PASS: 13 positive cases and 2 unsupported cases (15/15); Recall@5 13/13,
symbol accuracy 13/13, citation accuracy 13/13, unsupported abstention 2/2.

PYTHONPATH=src python evals/run_multirepo_ground_truth.py --root . --output multirepo_ground_truth_results.json
PASS: 41/41 cases; Recall@1 29/31, Recall@5 31/31, MRR@5 0.9543,
source-range validity 31/31, symbol-range accuracy 13/13, unsupported
abstention 10/10; source mode `git_revision`, RepoPilot revision verified.

PYTHONPATH=src python evals/run_multirepo_ground_truth.py --root . --use-checkout
EXPECTED NON-PASS: 40/41 because the current worktree uses the newer
`read_safe_text` range 238-330 while this dataset targets the recorded
8f9a8c... baseline range 236-328. The explicit checkout mode is available for
proposed-change testing and correctly exposes this mismatch.

python -m pytest tests/test_multirepo_ground_truth.py tests/test_provider_eval.py
PASS: 15 passed after the revision-materialization regression test

python -m pytest
PASS: 89 passed in 12.11s

python -m ruff check .
PASS: All checks passed

python -m mypy src
PASS: no issues found in 9 source files

python -m compileall -q src evals tests
PASS: completed without errors

docker compose config -q
EXPECTED FAIL: required REP_PILOT_API_TOKEN is absent outside Doppler

doppler run -- docker compose config -q
PASS: Compose configuration resolved without output or secret disclosure

Set-Location apps/web; npm audit --audit-level=high
PASS: found 0 vulnerabilities

npm run build
PASS: TypeScript compilation and Vite production build completed

git diff --check
PASS: no whitespace errors
```

The first command validates retrieval, symbol, citation, and abstention
behavior. It does not prove semantic fact entailment; the tables above supply
the maintainer/AI-assisted source review. No live-provider evaluation or
external penetration test was performed as part of this audit.

## Unresolved issues and limitations

1. The default RepoPilot multirepository source is an isolated archive of the
   recorded Git revision. The supplied checkout must contain that revision;
   `--use-checkout` intentionally bypasses this guarantee for proposed-change
   testing.
2. The audit is AI-assisted maintainer work, not independent second-person
   review. A human reviewer should recheck every expected fact, path, range,
   and unsupported query before publishing external accuracy claims.
3. Offline lexical retrieval metrics, even when all cases pass, do not measure
   broad semantic retrieval, live-provider answer quality, production
   behavior, or resistance to an external penetration test.
