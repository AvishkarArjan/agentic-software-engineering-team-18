# Team 18 - Task 3 implementation

## Setup and commands

Run from the lab1 directory with Python 3.11 or newer. Install numpy, rank-bm25,
tiktoken, openai, python-dotenv and pytest (the supplied requirements file also
contains the dependencies for other tasks). requirements.lock.txt records the
actual environment used for the submitted measurements; it is not a requirement
to use Python 3.14 or these exact newest versions.

Copy .env.example to .env in the lab1 root, fill in the UPB gateway key, and connect
the university VPN. Do not commit .env. Defaults are openai.gpt-6-luna for chat and
kiconnect.qwen3-embedding-8b for embeddings. LAB_CHAT_MODEL and LAB_EMBEDDING_MODEL
override these defaults. Keep the same models for a comparison run.

```powershell
python -m task3_rag.run_experiments retrieval
python -m task3_rag.run_experiments generation
python -m task3_rag.summarize
python -m pytest task3_rag/test_retrieval.py -q
python -m task3_rag.verify_results
```

The first two commands can instead be run as `python -m
task3_rag.run_experiments all`. Each uses up to four worker threads, sharing a
request spacer targeting fewer than 80 requests per minute. Gateway retries
are handled by the supplied LLMClient. Retry traffic can increase this rate.

The retrieval command builds every index and evaluates R1--R5, all recursive
chunk-size settings, and three hybrid weights. The generation command selects
the two best held-out retrieval configurations, generates answers to the same
50 questions selected by judge.py --sample 50, and invokes the provided Judge
class for faithfulness, answer relevance and correctness. It then generates
all 100 test predictions with the selected configuration.

The supplied run also includes a separate offline lexical-index benchmark
(`python -m task3_rag.benchmark_lexical_index`).
`python -m task3_rag.evidence_review` attaches the questions, answers, contexts and
source documents to our ten hand-checked judge decisions
(results/judge_review_10.jsonl). Neither makes additional LLM requests. `python -m task3_rag.package_solution` creates the
standalone delivery ZIP, scanning included files for the locally configured key
and excluding the embedding cache. The original evaluator and judge remain intact.

Answer generation and judging append completed items immediately and skip those
IDs on restart. Embeddings are cached by hash of model ID and exact text in
.cache/embeddings.sqlite. Rewrites are saved in results/rewrites.jsonl. If changing
the corpus, prompts, models or algorithm, use a fresh results/cache/log directory:
saved completion rows are keyed by question ID and must not be mixed across
different experimental conditions. Rerunning retrieval with a warm cache measures
warm-cache indexing and overwrites timing summaries; preserve the first-run
results before doing so.

## Retrieval designs

Every chunk includes its source document ID, type, title and version. Chunk sizes
are measured with cl100k_base, including metadata. All experiments use 32 tokens
of overlap. Recursive chunking prefers Markdown headings, then paragraphs, then
sentence boundaries, finally fixed token windows for oversized units. Splits
may fall inside code/tables; this is a known limitation. Long units reserve
capacity for overlap. A source document may yield several chunks.

- **R1:** BM25Okapi on exactly the selected R3 chunk objects. Tokenization keeps
  exact dotted/underscored/hyphenated identifiers and also indexes their parts.
- **R2:** Fixed token windows, size 220, overlap 32; dense cosine similarity.
- **R3:** Recursive chunks, comparing sizes 120, 220 and 360 with the same
  overlap 32; dense cosine similarity. Document and query vectors are L2-normalized.
- **R4:** `alpha * minmax(BM25) + (1-alpha) * minmax(cosine)`, normalized per
  query over the same chunks. Constant-score channels contribute zeros. The
  lexical weight alpha is selected from 0.25, 0.5 and 0.75 on tuning questions.
- **R5:** R4 plus query rewriting. The chat model preserves identifiers and
  versions while expanding descriptive phrases to technical vocabulary. It never
  receives dev answers or relevance labels. R5 averages the R4 scores of the
  original query and rewritten query, limiting the effect of rewrite drift.

Results contain the top five unique source documents, each represented by its
highest-ranked chunk. This matches document-level scoring and prevents one long
document consuming all five slots. The generator receives exactly these five
chunk texts, saved verbatim in its answers JSONL. It does not receive full
documents, ground-truth answers, categories or relevance labels.

## Experimental protocol

Before tuning, a seed-18 stratified split assigns 50 dev questions (10/category)
to tuning and 100 (20/category) to held-out evaluation. Since unanswerable
questions have no relevance labels, retrieval metrics use 40 tuning and 80
held-out answerable questions. Every config is also reported on the full 150 dev
set (120 answerable), clearly labelled as including tuning data.

Choose recursive size and alpha using tuning recall@5; break ties with rank-aware
precision@5. Compare final R1--R5 on the held-out set, select the top two using
the same ordering, and run the official seed-0 stratified 50-question judge
sample. This standard sample overlaps both the tuning and held-out subsets, so
its scores are development results rather than an independent test estimate.
Choose the test-generation configuration using mean dev judge correctness;
break ties with the held-out retrieval ranking. Hidden test labels are neither
available nor used. This does not establish a hidden-test improvement over R1;
the report measures improvement on dev only.

The answer prompt prioritizes official references, distinguishes old versions
from current defaults, rejects undocumented identifiers, and uses the assignment's
exact abstention sentence when evidence is insufficient. No answer is copied
from the ground truth. The provided evaluator and judge are unchanged; the runner
calls their functions directly rather than reimplementing scoring. You can verify:

```powershell
python task3_rag/evaluate.py task3_rag/results/retrieval_r1.jsonl --k 5
```

For an independent judge rerun, use the provided judge.py command with an
answers_CONFIG.jsonl file and --sample 50. It makes additional paid calls and
may change verdicts; preserve the original results first.

## Deliverables and limitations

- retrieval.py: chunking, tokenization, normalized fusion and ranked retrieval.
- run_experiments.py: indexing, cached embeddings, split/tuning/evaluation,
  rewriting, answer generation, provided-judge orchestration and test output.
- summarize.py: reproducible metric CSV, Markdown tables and usage totals.
- results/: per-question retrieval, metrics, exact contexts/answers, judge
  claims/verdicts, tuning decisions and timing.
- logs/: full gateway requests/responses and usage, excluding keys.
- predictions_test.jsonl: 100 answers and ranked document IDs for submission.
- ANALYSIS.md: findings, failures, recommendation, and independent evidence audit.

Min-max normalization is sensitive to outliers. A single source chunk may omit
details located elsewhere in its document. Rewriting may hallucinate synonyms.
LLM answers and judge decisions are fallible. A shared generator/judge model can
introduce correlated errors. Token counts are estimates for the gateway
models. Batch embedding timings are not individual interactive query timings.
Indexing runs share a content-addressed vector cache, so later settings reuse
some identical chunks; index_timing.json exposes new/hit counts rather than
claiming all indexes were fully cold.

Never submit .env, the virtual environment, or .cache/. Large vector caches are
excluded from the delivery archive. Use a fresh environment and rerun for an
independent reproduction; all API use requires the gateway and VPN.
