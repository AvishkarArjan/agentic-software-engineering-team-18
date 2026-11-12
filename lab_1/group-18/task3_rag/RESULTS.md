# Task 3 measured results

## Retrieval on held-out development questions

Values are recall@5 / rank-aware precision@5. Unanswerable questions are excluded by the supplied evaluator.

| Config | Overall | Identifier | Paraphrase | Multi-hop | Version |
| --- | --- | --- | --- | --- | --- |
| r1 | 0.512 / 0.515 | 0.900 / 0.708 | 0.100 / 0.062 | 0.500 / 0.738 | 0.550 / 0.550 |
| r2 | 0.544 / 0.475 | 0.550 / 0.485 | 0.950 / 0.806 | 0.025 / 0.010 | 0.650 / 0.597 |
| r3_120 | 0.544 / 0.466 | 0.550 / 0.525 | 0.900 / 0.777 | 0.025 / 0.025 | 0.700 / 0.538 |
| r3_220 | 0.544 / 0.478 | 0.550 / 0.485 | 0.950 / 0.812 | 0.025 / 0.010 | 0.650 / 0.604 |
| r3_360 | 0.531 / 0.467 | 0.550 / 0.485 | 0.950 / 0.812 | 0.025 / 0.010 | 0.600 / 0.562 |
| r3 | 0.544 / 0.478 | 0.550 / 0.485 | 0.950 / 0.812 | 0.025 / 0.010 | 0.650 / 0.604 |
| r4 | 0.706 / 0.653 | 1.000 / 0.756 | 0.700 / 0.589 | 0.475 / 0.691 | 0.650 / 0.575 |
| r5 | 0.731 / 0.676 | 1.000 / 0.756 | 0.800 / 0.679 | 0.475 / 0.698 | 0.650 / 0.573 |

## Index construction

| Config | Chunks | Index seconds | New vectors | Cached vectors | Index reference |
| --- | --- | --- | --- | --- | --- |
| r1 | 973 | 0.168 | 0 | 0 | offline BM25 timing |
| r2 | 970 | 27.636 | 970 | 0 | r2 |
| r3_120 | 1902 | 49.805 | 1902 | 0 | r3_120 |
| r3_220 | 973 | 21.760 | 711 | 262 | r3_220 |
| r3_360 | 952 | 1.050 | 27 | 925 | r3_360 |
| r3 | 973 | 21.760 | 711 | 262 | shared r3_220 |
| r4 | 973 | 21.760 | 711 | 262 | shared r3_220 |
| r5 | 973 | 21.760 | 711 | 262 | shared r3_220 |

R3/R4/R5 share the selected base index; their repeated times describe the same construction, not three independent builds. Later chunk-size settings reuse identical text vectors. R2 indexing time excludes its preceding chunk-construction step; recursive timings include it. R1 is measured separately without vector construction.

## Retrieval on all 150 development questions (120 answerable)

These numbers include the tuning subset; use the held-out table above for comparison without parameter-tuning overlap.

| Config | Overall | Identifier | Paraphrase | Multi-hop | Version |
| --- | --- | --- | --- | --- | --- |
| r1 | 0.546 / 0.552 | 0.900 / 0.725 | 0.167 / 0.082 | 0.483 / 0.769 | 0.633 / 0.633 |
| r2 | 0.558 / 0.491 | 0.567 / 0.507 | 0.933 / 0.776 | 0.033 / 0.018 | 0.700 / 0.665 |
| r3_120 | 0.546 / 0.475 | 0.567 / 0.533 | 0.867 / 0.736 | 0.017 / 0.017 | 0.733 / 0.616 |
| r3_220 | 0.558 / 0.498 | 0.567 / 0.507 | 0.933 / 0.798 | 0.033 / 0.018 | 0.700 / 0.669 |
| r3_360 | 0.550 / 0.491 | 0.567 / 0.507 | 0.933 / 0.798 | 0.033 / 0.018 | 0.667 / 0.642 |
| r3 | 0.558 / 0.498 | 0.567 / 0.507 | 0.933 / 0.798 | 0.033 / 0.018 | 0.700 / 0.669 |
| r4 | 0.717 / 0.688 | 1.000 / 0.790 | 0.700 / 0.551 | 0.467 / 0.761 | 0.700 / 0.650 |
| r5 | 0.742 / 0.724 | 1.000 / 0.790 | 0.800 / 0.694 | 0.467 / 0.765 | 0.700 / 0.648 |

## Latency and retrieved context size

| Config | Mean local scoring ms | Mean composed query seconds | Mean context tokens | Approx generator input tokens/query |
| --- | --- | --- | --- | --- |
| r3_120 | 5.647 | 0.029 | 501.8 | 646.7 |
| r3_220 | 2.649 | 0.026 | 744.7 | 890.5 |
| r3_360 | 2.785 | 0.026 | 759.5 | 905.3 |
| r2 | 3.233 | 0.027 | 748.0 | 892.6 |
| r1 | 2.469 | 0.002 | 822.7 | 968.7 |
| r3 | 3.201 | 0.027 | 744.7 | 890.5 |
| r4 | 2.623 | 0.026 | 794.9 | 941.0 |
| r5 | 5.388 | 3.742 | 799.0 | 945.2 |

Composed query time sums measured scoring, batch-amortized query embedding, and (R5) actual rewrite request/wait time plus batch-amortized rewrite embedding. It is not a measured single-request production latency. Shared embeddings are charged to each dense configuration analytically; no double API billing is implied. Query vectors are reused for fair score comparisons.

## Gateway usage

| Phase | Logged operations | Prompt tokens | Completion tokens | Reported USD | Missing cost fields |
| --- | --- | --- | --- | --- | --- |
| embedding | 131 | 0 | 0 | 0.000000 | 0 |
| gateway | 2 | 10 | 5 | 0.000003 | 0 |
| generate | 200 | 188720 | 8234 | 0.024048 | 0 |
| judge | 357 | 82365 | 21468 | 0.019128 | 0 |
| rewrite | 250 | 23631 | 27455 | 0.016091 | 0 |

Embedding operations may contain multiple HTTP batches. Reasoning tokens are included in completion-token accounting by the gateway; do not add them twice. Costs are gateway-reported, not estimated prices. The helper cache_hit field is only its response-header heuristic; it is not proof of a cold request. Local vector cache hits are recorded separately.

## End-to-end judge (same stratified 50 questions, seed 0)

| Config | Category | N | Abstained | Faithfulness | Relevance | Correctness |
| --- | --- | --- | --- | --- | --- | --- |
| r4 | OVERALL | 50 | 22 | 1.000 | 0.605 | 0.760 |
| r4 | identifier | 10 | 0 | 1.000 | 0.734 | 1.000 |
| r4 | multi-hop | 10 | 10 | - | 0.381 | 0.000 |
| r4 | paraphrase | 10 | 2 | 1.000 | 0.650 | 0.800 |
| r4 | unanswerable | 10 | 10 | - | 0.444 | 1.000 |
| r4 | version | 10 | 0 | 1.000 | 0.814 | 1.000 |
| r5 | OVERALL | 50 | 21 | 1.000 | 0.603 | 0.780 |
| r5 | identifier | 10 | 0 | 1.000 | 0.722 | 1.000 |
| r5 | multi-hop | 10 | 10 | - | 0.404 | 0.000 |
| r5 | paraphrase | 10 | 1 | 1.000 | 0.676 | 0.900 |
| r5 | unanswerable | 10 | 10 | - | 0.410 | 1.000 |
| r5 | version | 10 | 0 | 1.000 | 0.804 | 1.000 |

## Costs attributed to configurations

| Config | Retrieval rewrite USD | Generation USD | Judge USD |
| --- | --- | --- | --- |
| r1 | 0.000000 | 0.000000 | 0.000000 |
| r2 | 0.000000 | 0.000000 | 0.000000 |
| r3 | 0.000000 | 0.000000 | 0.000000 |
| r4 | 0.000000 | 0.005848 | 0.009276 |
| r5 | 0.016091 | 0.018200 | 0.009852 |

Shared corpus/query embeddings are free on this gateway and reported separately above. R1 performs no API calls at retrieval time. R2/R3/R4 use a query embedding; R5 also uses a rewrite chat call and second query embedding. R5 rewrite cost here covers 150 dev plus 100 test queries. Generation/judge costs reflect only configurations actually run, including test generation for the winner; zeros for other configurations mean not run, rather than a measured zero-cost generation.
