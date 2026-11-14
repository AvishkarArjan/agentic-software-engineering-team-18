# Reproducing the Task 3 results (Team 18)

This guide explains how to reproduce every number in `RESULTS.md`, `ANALYSIS.md` and
`predictions_test.jsonl` from a fresh clone of the repository. It has two levels:

| Level | Needs | Time | Cost | What it reproduces |
|---|---|---|---|---|
| **A. Offline** | Python only | ~2 min | free | All metrics, tables, splits, the chunk-size and weight decisions, the R1 → R5 ranking, the R4/R5 winner, the R1 BM25 index (bit-exact), all chunkings, the judge-review file and the test-prediction format, all checked against the committed results |
| **B. Full re-run** | UPB AI Gateway key + VPN | ~1–2 h | ≈ $0.06 | Re-embeds the corpus, re-runs query rewriting, answer generation and judging from nothing |

Level A was last verified on **2026-11-14** on a fresh clone of commit `a74c43c` (Windows 11,
Python 3.14.6, new virtual environment, no `.cache/`, no `.env`). Every check passed. The
results are in the [verification record](#verification-record-2026-11-14).

---

## 0. Get a clean copy

```bash
git clone https://github.com/AvishkarArjan/agentic-software-engineering-team-18.git
cd agentic-software-engineering-team-18/lab_1/group-18
```

**Run every command below from `lab_1/group-18`**, the folder that contains `common/` and
`task3_rag/`. The scripts are run as modules (`python -m task3_rag.<script>`) and import
`common.llm_client`, so they won't work from inside `task3_rag/`. (`SOLUTION_README.md` calls
this folder "the lab1 directory"; in this repository it is `lab_1/group-18`.)

The relevant layout:

```
lab_1/group-18/
├── .env.example            # template; copy to .env only for Level B
├── common/llm_client.py    # gateway client (loads lab_1/group-18/.env)
└── task3_rag/
    ├── data/               # corpus.jsonl (932 docs), questions_dev.jsonl (150), questions_test.jsonl (100)
    ├── evaluate.py         # provided retrieval evaluator (unchanged)
    ├── judge.py            # provided LLM judge (unchanged)
    ├── retrieval.py        # chunking, BM25 tokenizer, normalized fusion, retriever
    ├── run_experiments.py  # full pipeline (gateway): retrieval phase + generation phase
    ├── summarize.py        # rebuilds RESULTS.md, retrieval_metrics.csv, cost files (offline)
    ├── verify_results.py   # recomputes every metric file and checks all outputs (offline)
    ├── evidence_review.py  # rebuilds results/judge_review_10.jsonl (offline)
    ├── benchmark_lexical_index.py  # offline BM25 build timing
    ├── test_retrieval.py   # unit tests (offline)
    ├── results/            # all committed experiment outputs
    ├── logs/               # 552 gateway request/response logs (no keys)
    └── predictions_test.jsonl
```

## 1. Create a fresh environment

Python 3.11 or newer. `requirements.lock.txt` pins the exact versions used for the submitted
results. `requirements.txt` gives the minimum versions.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-cache-dir -r task3_rag\requirements.lock.txt
```

**Linux / macOS (bash)**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-cache-dir -r task3_rag/requirements.lock.txt
```

Alternative with uv: `uv venv && uv pip install -r task3_rag/requirements.lock.txt`, then prefix
the commands below with `uv run`.

> `tiktoken` downloads the `cl100k_base` encoding (~1.7 MB) the first time it runs, so you need
> internet access for that step. Set `TIKTOKEN_CACHE_DIR` to an empty folder if you want to
> make sure no cached copy is used.

---

## Level A: offline reproduction (no API key)

### A1. Unit tests

```bash
python -m pytest task3_rag/test_retrieval.py -q -p no:cacheprovider
```

Expected: `7 passed`. The tests cover chunk size limits and document provenance (recursive and
fixed chunking), identifier tokenization (`PQ-E4663`, `spool.buffer_bytes` and their parts),
min-max scaling, one-chunk-per-document ranking, multi-hop group recall and rank-aware
precision, and exclusion of unanswerable questions.

### A2. Recompute every metric file and validate all outputs

```bash
python -m task3_rag.verify_results
```

Expected:

```
Verified: all metric files reproduce; two complete 50-question judge runs; exact contexts; 100 valid test predictions.
```

What this checks:

- `results/split.json`: the tuning and held-out sets don't overlap and together make up all 150 dev questions.
- For each of `r1, r2, r3_120, r3_220, r3_360, r3, r4, r5`, the 24 `metrics_<cfg>_{all_dev,tuning,heldout}.json` files are recomputed from `retrieval_<cfg>.jsonl` with the **provided** `evaluate.py` and must be **exactly equal** to the committed files.
- `answers_r4/r5.jsonl` and `judge_r4/r5.jsonl` each cover the same 50 questions as `judge.py --sample 50`, and every answer's `contexts` matches the retrieval output exactly.
- `predictions_test.jsonl` has 100 rows with exactly `id`, `answer` and `retrieved_doc_ids`, 5 unique valid doc IDs per row, and is the exact projection of `results/answers_r5_test.jsonl`.

### A3. Regenerate the derived files and compare them with git

```bash
python -m task3_rag.summarize        # RESULTS.md, results/retrieval_metrics.csv, cost_summary.json, cost_per_configuration.csv
python -m task3_rag.evidence_review  # results/judge_review_10.jsonl
git status --short
git diff --ignore-cr-at-eol --stat
```

Expected: `summarize` prints
`Wrote RESULTS.md, results/retrieval_metrics.csv, results/cost_summary.json`, and
`evidence_review` prints `Saved 10 source-checked decisions; correctness agreement 10/10.`

`git diff --ignore-cr-at-eol --stat` should print **nothing**: the regenerated files are
identical to the ones on GitHub.

> **Windows note:** `git status` will still list the five regenerated files as modified, because
> Python writes CRLF line endings on Windows. `--ignore-cr-at-eol` shows that line endings are the
> only difference. On Linux/macOS, plain `git status` is already clean.

### A4. Run the provided evaluator by hand (spot check)

```bash
python task3_rag/evaluate.py task3_rag/results/retrieval_r5.jsonl --k 5
```

Expected (all 150 dev questions; unanswerable questions are excluded by the evaluator):

```
category         n    recall  precision
identifier      30     1.000      0.790
multi-hop       30     0.467      0.765
paraphrase      30     0.800      0.694
version         30     0.700      0.648
OVERALL        120     0.742      0.724
```

These numbers match the `r5` row of the all-dev table in `RESULTS.md`. Replace `r5` with
`r1`, `r2`, `r3_120`, `r3_220`, `r3_360`, `r3` or `r4` to check the other rows.
Adding `--json out.json` writes a file identical to `results/metrics_r5_all_dev.json`.

### A5. Rebuild R1 (BM25) and every chunk index yourself

R1 needs no embeddings, so you can rebuild it completely from the raw corpus. Save this as
`check_r1.py` in `lab_1/group-18` (or paste it into `python -`):

```python
import json
from pathlib import Path
from task3_rag.evaluate import load_jsonl
from task3_rag.retrieval import chunk_corpus, Retriever

H, R = Path('task3_rag'), Path('task3_rag/results')
docs = load_jsonl(H / 'data/corpus.jsonl')
idx = json.loads((R / 'index_timing.json').read_text())

# 1) every chunking reproduces: chunk counts and the exact text of every saved context
built = {}
for name, size, rec in [('r3_120', 120, True), ('r3_220', 220, True), ('r3_360', 360, True), ('r2', 220, False)]:
    chunks = chunk_corpus(docs, size, 32, recursive=rec)
    built[name] = {c.chunk_id: c.text for c in chunks}
    print(name, 'chunks', len(chunks), 'expected', idx[name]['chunks'])
base = json.loads((R / 'selection.json').read_text())['selected_recursive']   # 'r3_220'
for cfg, cs in [('r1', base), ('r2', 'r2'), ('r3_120', 'r3_120'), ('r3_220', 'r3_220'),
                ('r3_360', 'r3_360'), ('r3', base), ('r4', base), ('r5', base)]:
    bad = sum(built[cs].get(cid) != t
              for s in ('', '_test') for r in load_jsonl(R / f'retrieval_{cfg}{s}.jsonl')
              for cid, t in zip(r['chunk_ids'], r['contexts']))
    print(f'{cfg}: context mismatches = {bad}')

# 2) R1 rebuilt from scratch: rankings and BM25 scores must match exactly
bm25 = Retriever(chunk_corpus(docs, int(base.split('_')[1]), 32, recursive=True))
for s, qfile in (('', 'questions_dev'), ('_test', 'questions_test')):
    saved = {r['id']: r for r in load_jsonl(R / f'retrieval_r1{s}.jsonl')}
    diff = 0
    for q in load_jsonl(H / f'data/{qfile}.jsonl'):
        hits = bm25.retrieve(q['question'], mode='bm25')
        diff += ([h['chunk_id'] for h in hits] != saved[q['id']]['chunk_ids'] or
                 [h['score'] for h in hits] != saved[q['id']]['scores'])
    print(f'retrieval_r1{s}.jsonl: rows that differ = {diff}')
```

```bash
python check_r1.py
```

Expected: chunk counts **1902 / 973 / 952 / 970** (R3-120 / R3-220 / R3-360 / R2), each matching
`index_timing.json`; `context mismatches = 0` for all eight configurations; and
`rows that differ = 0` for both the dev and test R1 files. The BM25 scores are bit-identical.

This shows that the chunk text sent to the dense retrievers (R2–R5) and to the generator is
exactly what `retrieval.py` produces from the corpus. Only the embedding vectors themselves need
the gateway.

### A6. Decisions that follow from the saved results

Each of these can be recomputed from committed files with the provided `evaluate.py` and
`judge.stratified_sample` (all were checked in the verification run):

| Decision | Where it's recorded | How it's derived | Value |
|---|---|---|---|
| Tuning/held-out split | `results/split.json` | `stratified_sample(dev, 50, seed=18)`: 50 tuning, 100 held-out | reproduces exactly |
| Recursive chunk size | `results/selection.json` | highest tuning recall@5 of `r3_120/220/360`, precision@5 breaks ties | `r3_220` (0.5875 / 0.538; `r3_360` ties exactly on both, and `max()` keeps the first, smaller size) |
| Hybrid weight α (BM25 share) | `results/selection.json` | highest tuning recall@5 over α ∈ {0.25, 0.5, 0.75}, precision breaks ties | `0.5` (0.7375 / 0.758) |
| Configuration ranking | `results/ranking.json` | held-out recall@5, then precision@5 | `r5 > r4 > r3 > r2 > r1` |
| End-to-end pair | `results/ranking.json` | top two | `r5`, `r4` |
| Deployed configuration | `results/best.json` | mean judge correctness on the 50-question sample | `r5` (0.78 vs 0.76) |
| `r3` = selected `r3_220` | `retrieval_r3*.jsonl` | identical except the wall-clock field `scoring_s` | identical |

### A7. Optional: offline BM25 build timing

```bash
python -m task3_rag.benchmark_lexical_index
```

This prints `BM25: 973 chunks, ~0.17s including chunking.` and **overwrites**
`results/lexical_index_timing.json`. The chunk count is deterministic; the seconds are
wall-clock time and will differ a little (about 1% in the verification run). Run
`git checkout -- task3_rag/results/lexical_index_timing.json` to restore the committed file.

---

## Level B: full re-run against the UPB AI Gateway

This repeats the experiment from scratch. It needs a personal gateway key and the university
network or VPN.

### B1. Configure

```bash
cp .env.example .env        # in lab_1/group-18 (common/llm_client.py loads this exact file)
# edit .env: set UPB_AI_GATEWAY_KEY=...  (never commit .env; it is already in .gitignore)
```

Keep the models that produced the submitted results:

```
LAB_CHAT_MODEL=openai.gpt-6-luna
LAB_EMBEDDING_MODEL=kiconnect.qwen3-embedding-8b
```

### B2. Move the committed outputs aside first (important)

The runner **resumes**. It skips any question ID already in `results/rewrites.jsonl`,
`answers_*.jsonl` or `judge_*.jsonl`, and the gateway client **appends** to `logs/*.jsonl`.
If you run it on top of the committed files, no new answers or judgments are generated, and new
logs mix with the old ones, which double-counts the costs in `summarize`. So move both
folders out of the way and keep them as the reference:

```bash
mv task3_rag/results task3_rag/results_github
mv task3_rag/logs    task3_rag/logs_github
cp task3_rag/predictions_test.jsonl task3_rag/predictions_test_github.jsonl
```

PowerShell: `Rename-Item task3_rag\results results_github`, `Rename-Item task3_rag\logs logs_github`,
`Copy-Item task3_rag\predictions_test.jsonl task3_rag\predictions_test_github.jsonl`.

Don't commit these renamed folders. Do this in a separate clone, or restore with `git checkout`
afterwards.

### B3. Run

```bash
python -m task3_rag.run_experiments retrieval    # embeds 250 queries + all chunkings, rewrites 250 queries, evaluates R1–R5
python -m task3_rag.run_experiments generation   # 2 configs × 50 answers + judge, then 100 test answers with the winner
python -m task3_rag.summarize
python -m pytest task3_rag/test_retrieval.py -q
python -m task3_rag.verify_results
```

(`python -m task3_rag.run_experiments all` runs both phases.) Requests are spaced to under
80 per minute across 4 worker threads, so plan for roughly 1–2 hours. The submitted run made
about 940 gateway calls: embeddings are free, and rewrite + generation + judge cost
**$0.059 in total** (`results/cost_summary.json`). Embeddings are cached in
`task3_rag/.cache/embeddings.sqlite`, which is about 4096 floats per text. Never commit or
submit it.

### B4. Compare with the committed results

```bash
python task3_rag/evaluate.py task3_rag/results/retrieval_r1.jsonl --k 5     # compare to results_github
diff <(python -c "import json;[print(json.loads(l)['retrieved_doc_ids']) for l in open('task3_rag/results/retrieval_r1.jsonl')]") \
     <(python -c "import json;[print(json.loads(l)['retrieved_doc_ids']) for l in open('task3_rag/results_github/retrieval_r1.jsonl')]")
```

What to expect:

| Output | Expected agreement | Why |
|---|---|---|
| `split.json`, chunk counts, R1 retrieval and metrics | **identical** | deterministic, no model involved |
| R2 / R3 / R4 retrieval and metrics | identical or within ±0.01 | embeddings from the same model are near-deterministic; tiny float differences can swap near-tied chunks |
| `rewrites.jsonl`, R5 retrieval | usually identical (the gateway caches identical requests), otherwise close | LLM rewriting is not guaranteed deterministic |
| answers, judge scores, `predictions_test.jsonl` answers | close but **not** word-for-word | LLM generation and LLM judging are stochastic; the README warns that re-judging "may change verdicts" |
| timing and latency files | different | wall-clock measurements; the gateway cache also makes second runs faster |

`ANALYSIS.md`, `judge_review_10.jsonl` (the hand review in `evidence_review.py`) and
`failure_analysis_5.jsonl` describe the **committed** run. After a Level B re-run, the
committed `results_github/` remains the reference for them.

### B5. Restore the submitted state

```bash
rm -rf task3_rag/results task3_rag/logs task3_rag/.cache
mv task3_rag/results_github task3_rag/results
mv task3_rag/logs_github    task3_rag/logs
mv task3_rag/predictions_test_github.jsonl task3_rag/predictions_test.jsonl
git status   # should be clean apart from .env (ignored)
```

---

## Reference numbers

Held-out development questions (80 answerable), recall@5 / rank-aware precision@5, from
`RESULTS.md`:

| Config | Overall | Identifier | Paraphrase | Multi-hop | Version |
|---|---|---|---|---|---|
| R1 BM25 | 0.512 / 0.515 | 0.900 / 0.708 | 0.100 / 0.062 | 0.500 / 0.738 | 0.550 / 0.550 |
| R2 fixed + dense | 0.544 / 0.475 | 0.550 / 0.485 | 0.950 / 0.806 | 0.025 / 0.010 | 0.650 / 0.597 |
| R3-120 | 0.544 / 0.466 | 0.550 / 0.525 | 0.900 / 0.777 | 0.025 / 0.025 | 0.700 / 0.538 |
| R3-220 (selected) | 0.544 / 0.478 | 0.550 / 0.485 | 0.950 / 0.812 | 0.025 / 0.010 | 0.650 / 0.604 |
| R3-360 | 0.531 / 0.467 | 0.550 / 0.485 | 0.950 / 0.812 | 0.025 / 0.010 | 0.600 / 0.562 |
| R4 hybrid α=0.5 | 0.706 / 0.653 | 1.000 / 0.756 | 0.700 / 0.589 | 0.475 / 0.691 | 0.650 / 0.575 |
| R5 R4 + rewrite | 0.731 / 0.676 | 1.000 / 0.756 | 0.800 / 0.679 | 0.475 / 0.698 | 0.650 / 0.573 |

End-to-end judge, same stratified 50 dev questions (seed 0): R4 correctness **0.760**
(22 abstentions), R5 correctness **0.780** (21 abstentions); faithfulness 1.000 for both.

---

## Verification record (2026-11-14)

Fresh `git clone --depth 1` of `master` at commit `a74c43c`, a new virtual environment from
`requirements.lock.txt` (`pip --no-cache-dir`), a fresh `TIKTOKEN_CACHE_DIR`, no `.cache/` and
no `.env`.

| Check | Result |
|---|---|
| Corpus / dev / test sizes | 932 / 150 / 100 ✅ |
| `pytest task3_rag/test_retrieval.py` | 7 passed ✅ |
| `python -m task3_rag.verify_results` | all 24 metric files equal, judge runs complete, contexts exact, 100 valid predictions ✅ |
| `summarize` + `evidence_review` → `git diff --ignore-cr-at-eol` | empty (only Windows CRLF differences) ✅ |
| `evaluate.py --json` for R5 vs `metrics_r5_all_dev.json` | identical ✅ |
| `split.json` from seed 18 | identical ✅ |
| Chunk counts R3-120/220/360, R2 | 1902 / 973 / 952 / 970 = `index_timing.json` ✅ |
| Saved contexts of all 8 configurations (dev + test) vs freshly built chunks | 0 mismatches ✅ |
| R1 rebuilt from scratch vs `retrieval_r1.jsonl` and `retrieval_r1_test.jsonl` | 0 ranking differences, max score difference 0.0 ✅ |
| Chunk size, α, ranking and best-configuration decisions | all reproduce ✅ |
| `predictions_test.jsonl` doc IDs = `retrieval_r5_test.jsonl` | identical ✅ |
| `rewrites.jsonl` | covers all 250 dev + test queries ✅ |
| `benchmark_lexical_index` | 973 chunks; time 0.169 s vs 0.168 s committed (wall clock) ✅ |

Not re-run in this verification, because no gateway key was available: corpus/query embeddings,
query rewriting, answer generation and LLM judging (Level B). Those outputs were checked for
internal consistency (the exact contexts passed to the generator, complete 50-question judge
files, predictions derived from the R5 answers), but they were not regenerated.
