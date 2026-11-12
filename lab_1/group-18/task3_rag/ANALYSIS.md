# Task 3 analysis - Team 18

The selected configuration is **R5**. On the held-out development questions, its document recall@5 is 0.73125, versus 0.51250 for R1: an absolute improvement of 0.21875. These are development results; hidden-test correctness and improvement cannot be established without the withheld labels.

## What the comparison shows

BM25 handles exact identifiers well: held-out identifier recall is 0.900, but paraphrase recall is only 0.100. Dense recursive retrieval reverses that pattern: identifier recall is 0.550 and paraphrase recall 0.950. Neither alone covers both query styles reliably. R4 raises identifier recall to 1.000 while recovering 0.700 of paraphrase questions. R5 keeps identifier recall at 1.000 and raises paraphrase recall to 0.800. It improves aggregate held-out recall from R4's 0.70625 to 0.73125, but does not improve multi-hop recall (both 0.475). The hybrid weight is applied to BM25, not to the dense channel.

Tuning selected r3_220 and lexical weight 0.5. At alpha 0.25 and 0.50, tuning recall tied at 0.7375; alpha 0.50 won on precision (0.758125 versus 0.727083). Alpha 0.75 reduced recall to 0.6625. Thus equal weighting follows the declared tuning rule, rather than choosing a weight after seeing held-out results.

## Chunk-size comparison

All sizes include metadata and use 32-token overlap. Size 120 produces 1,902 chunks; 220 produces 973; 360 produces 952. Many documents fit whole at 220, so 360 offers little additional coverage. Sizes 220 and 360 tie on tuning recall and precision; the earlier/smaller 220 setting wins the deterministic tie. On held-out data, 120 and 220 both reach dense recall 0.54375, while 360 reaches 0.53125. Size 220 has higher precision than 120 (0.477917 versus 0.466250). Smaller chunks can separate setting explanations from default tables and introduce generic fragments; larger chunks make long release-note chunks less focused. The modest differences do not justify a universal claim about optimal chunk size. Index times in RESULTS.md expose substantial cache reuse for 360; its low indexing time is not evidence of inherently faster cold embedding.

## End-to-end quality and abstention

R5: correctness 0.780, 21/50 abstentions, mean scored faithfulness 1.000 across 29 non-abstaining answers. See RESULTS.md for all category-level scores.

R4: correctness 0.760, 22/50 abstentions, mean scored faithfulness 1.000 across 28 non-abstaining answers. See RESULTS.md for all category-level scores.

The exact abstention prompt prevents unsupported numeric guesses, but an abstention can still be wrong when retrieval missed available evidence. R5 gets all 10 unanswerable cases right and all 10 multi-hop cases wrong. Its faithfulness 1.000 excludes abstentions; it does not imply 100% task accuracy. Multi-hop needs a second retrieval based on the discovered error/setting name. Query rewriting sees only the original question, so it cannot reliably discover that missing name.

The judge sample is the supplied seed-0 stratified sample of 50, with 10 questions per category. Parameter tuning used a separate seed-18 split, but this prescribed end-to-end sample overlaps both parts. Treat these as development comparisons, not an untouched test estimate. The same model generates and judges answers, creating a possible shared-model bias.

## Ten independently source-checked judge decisions

We checked these exact answers and retrieved contexts by hand against the corpus and reference answers, without issuing another judge call. Full passages and independent verdicts are saved in results/judge_review_10.jsonl.

| ID     | Category     | Judge correctness | Review | Evidence / reasoning                                                                                                                                                                                                                                                                                                               |
| ------ | ------------ | ----------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| dev008 | identifier   | 1                 | Agree  | The current metrics.interval_s table gives Default 10 and Unit s. The answer correctly ignores three forum replies and the 2.x page giving 300.                                                                                                                                                                                    |
| dev061 | identifier   | 1                 | Agree  | The pq topic restore CLI flag table defines --tenant as the name of the tenant the command applies to; the answer repeats that meaning without adding behavior.                                                                                                                                                                    |
| dev004 | paraphrase   | 1                 | Agree  | Both versioned dlq.max_retries pages describe retry attempts of the dead-letter handler. No numeric default was requested, so identifying the setting is sufficient.                                                                                                                                                               |
| dev087 | paraphrase   | 0                 | Agree  | The correct scheduler.max_connections reference exists in the corpus but is absent from all five retrieved passages. Their scheduler references concern buffer_bytes/log_level; none supports the requested connection limit. Abstention is safe on the supplied context but incorrect against the full documentation.             |
| dev009 | version      | 1                 | Agree  | The explicit 2.x compactor.compression page gives none. The current page gives lz4; the answer correctly selects the requested historical version.                                                                                                                                                                                 |
| dev037 | version      | 1                 | Agree  | The old dlq.timeout_ms table gives 30000 ms; the current table explicitly says Default changed in 4.0. Together they support both claims despite the labelled changelog d0690 not being retrieved. Correctness and faithfulness should both be 1.                                                                                  |
| dev013 | unanswerable | 1                 | Agree  | No exact spool.queue_capacity identifier occurs in the corpus. Retrieved queue_capacity entries belong to other components. The exact abstention is appropriate; faithfulness is unscored rather than zero.                                                                                                                        |
| dev059 | unanswerable | 1                 | Agree  | The corpus contains neither GDPR nor certification text; retrieved configuration entries provide no certification evidence. Abstention agrees with the reference answer. A top-five miss alone would not prove global absence; the corpus search supplies an additional check.                                                     |
| dev025 | multi-hop    | 0                 | Agree  | The retrieved INC-2024-171 report identifies PQ-E1915 but explicitly sends the reader to its error entry for the permanent fix. That entry is missing from the supplied context. The reference calls for capacity/load changes, not the incident rollback workaround; abstaining is therefore a retrieval-caused incorrect answer. |
| dev047 | multi-hop    | 0                 | Agree  | The error entry d0522 is retrieved and names acktracker.max_retries, but its configuration page d0749 with Default 20 is absent. The model cannot establish the numeric default from the retrieved forum replies. Judge correctness 0 for abstention is justified; the second retrieval hop failed.                                |

The review agrees with all ten correctness and faithfulness decisions; agreement is not proof that the judge is calibrated on unseen answers. Answer-relevance scores are not treated as correctness: a wrong answer or a generic abstention can still yield semantically related reverse-generated questions.

An instructive label limitation is dev037. The old configuration page d0311 explicitly gives 30000 ms, and the current page d0361 says the default changed in 4.0. The generated answer is correct and supported. Retrieval recall nevertheless scores zero because the labelled group contains only changelog d0690. We keep the supplied labels and scores unchanged and explain this discrepancy instead of patching the evaluation.

## Five actual failures of the selected system

All five answers below are the exact abstention sentence and were judged incorrect. After checking the retrieved passages, the primary cause is retrieval in each case; no fabricated generation failure is asserted.

### dev025: Missing incident-to-error hop

Which permanent fix does the documentation recommend for the error that caused incident INC-2024-171?

Expected: The incident was caused by PQ-E1915. Fix: Throttling protects the node. Add capacity or reduce load. As a last resort, raise `metrics.threshold_percent`.

Retrieved IDs: d0253, d0804, d0215, d0378, d0135. Required reference IDs: d0253, d0183.

The first-ranked incident d0253 identifies PQ-E1915 but contains only a rollback workaround and a reference to the error catalogue. The catalogue entry is not retrieved. The required permanent fix is to add capacity or reduce load, raising metrics.threshold_percent only as a last resort. The model correctly avoids presenting the workaround as the permanent fix, but its abstention is wrong against the full corpus.

Proposed improvement: Follow the error identifier discovered in the incident with a second retrieval query; reranking alone cannot add an absent source.

### dev042: Forum crowding hides the authoritative source

What is the current default value of the setting that the error catalogue recommends changing for PQ-E2051?

Expected: `compactor.compression` defaults to `lz4` in 4.x.

Retrieved IDs: d0785, d0770, d0879, d0736, d0841. Required reference IDs: d0738, d0564.

All five retrieved documents are compactor codec-mismatch forum threads. Their suggested settings conflict, and some replies explicitly defer to the catalogue. Neither the PQ-E2051 catalogue entry d0738 nor compactor.compression configuration d0564 is retrieved. The requested current default is lz4. The model abstains instead of treating forum guesses as authoritative.

Proposed improvement: Give exact error-catalogue matches an authority-aware candidate route, then retrieve the referenced setting. Evaluate that modification on fresh questions rather than silently adding it to these measured configurations.

### dev047: Error found, numeric configuration fact missing

What is the current default value of the setting that the error catalogue recommends changing for PQ-E2425?

Expected: `acktracker.max_retries` defaults to `20` in 4.x.

Retrieved IDs: d0576, d0517, d0522, d0116, d0855. Required reference IDs: d0522, d0749.

The catalogue entry d0522 appears at rank 3 and identifies acktracker.max_retries, but d0749 with its current default 20 is absent. Matching the original error code does not establish the default of the newly discovered setting. The generator abstains; this is a second-hop retrieval failure rather than a failure to read a retrieved numeric fact.

Proposed improvement: Extract the referenced configuration identifier from the error entry and retrieve its versioned reference page.

### dev087: Paraphrase remains semantically incomplete

Which setting limits how many clients can talk to the part that holds back messages until a later point in time in parallel?

Expected: The setting `scheduler.max_connections`.

Retrieved IDs: d0507, d0315, d0204, d0642, d0870. Required reference IDs: d0153.

The question describes delayed-message scheduling and simultaneous clients. Retrieval selects unrelated queue-capacity/connection-limit material and release-note snippets about other scheduler options. The actual scheduler.max_connections page d0153 is absent. The rewritten query did not make the complete component-plus-setting meaning competitive in the top five.

Proposed improvement: Try a cross-encoder or explicit component/setting decomposition as a separate future configuration; preserve the original query to limit rewrite drift.

### dev119: Threshold name found without its default

What is the current default value of the setting that the error catalogue recommends changing for PQ-E1799?

Expected: `retention.threshold_percent` defaults to `95` in 4.x.

Retrieved IDs: d0712, d0649, d0589, d0019, d0336. Required reference IDs: d0649, d0365.

The PQ-E1799 catalogue entry d0649 is retrieved at rank 2 and recommends retention.threshold_percent. The configuration document d0365 is absent, so the requested current default 95 is unavailable to the generator. A relevant error document covers only one of the two labelled information groups.

Proposed improvement: Follow configuration references and enforce evidence coverage of both the error-to-setting link and the versioned default.

## Deployment recommendation

Choose R5 for a controlled documentation-assistant pilot where answer coverage matters and an extra rewrite round trip is acceptable. It has the best held-out retrieval recall and the higher observed judge correctness. Keep explicit abstentions and source/version display. Its gain over R4 is small relative to the latency increase; R4 is the lower-latency alternative when that tradeoff dominates. The precise timings, token budgets and gateway-reported costs are in RESULTS.md.

Neither measured hybrid is ready for reliable multi-hop production use: R5 fails every multi-hop example in the judge sample. The next development step is evidence-driven second-hop retrieval with identifier and version checks, followed by evaluation on fresh held-out questions. Authority-aware ranking could reduce forum crowding. These are proposed follow-ups, not changes silently included after the reported evaluation.

The selected configuration generates all 100 predictions_test.jsonl rows. Hidden labels were never available; the measurable improvement over the R1 baseline is on development retrieval.
