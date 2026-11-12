"""Materialize the hand-checked judge review; no further LLM calls."""
from pathlib import Path
from task3_rag.evaluate import load_jsonl
from task3_rag.retrieval import write_jsonl

HERE=Path(__file__).resolve().parent

# These notes were authored after inspecting exact generated answers, retrieved
# passages, reference answers and corpus documents, independently of judge reasons.
REVIEWS={
    'dev008':(1.,1.,['d0171'],'The current metrics.interval_s table gives Default 10 and Unit s. The answer correctly ignores three forum replies and the 2.x page giving 300.'),
    'dev061':(1.,1.,['d0591'],'The pq topic restore CLI flag table defines --tenant as the name of the tenant the command applies to; the answer repeats that meaning without adding behavior.'),
    'dev004':(1.,1.,['d0032','d0303'],'Both versioned dlq.max_retries pages describe retry attempts of the dead-letter handler. No numeric default was requested, so identifying the setting is sufficient.'),
    'dev087':(0.,None,['d0153'],'The correct scheduler.max_connections reference exists in the corpus but is absent from all five retrieved passages. Their scheduler references concern buffer_bytes/log_level; none supports the requested connection limit. Abstention is safe on the supplied context but incorrect against the full documentation.'),
    'dev009':(1.,1.,['d0903'],'The explicit 2.x compactor.compression page gives none. The current page gives lz4; the answer correctly selects the requested historical version.'),
    'dev037':(1.,1.,['d0311','d0361'],'The old dlq.timeout_ms table gives 30000 ms; the current table explicitly says Default changed in 4.0. Together they support both claims despite the labelled changelog d0690 not being retrieved. Correctness and faithfulness should both be 1.'),
    'dev013':(1.,None,[],'No exact spool.queue_capacity identifier occurs in the corpus. Retrieved queue_capacity entries belong to other components. The exact abstention is appropriate; faithfulness is unscored rather than zero.'),
    'dev059':(1.,None,[],'The corpus contains neither GDPR nor certification text; retrieved configuration entries provide no certification evidence. Abstention agrees with the reference answer. A top-five miss alone would not prove global absence; the corpus search supplies an additional check.'),
    'dev025':(0.,None,['d0253'],'The retrieved INC-2024-171 report identifies PQ-E1915 but explicitly sends the reader to its error entry for the permanent fix. That entry is missing from the supplied context. The reference calls for capacity/load changes, not the incident rollback workaround; abstaining is therefore a retrieval-caused incorrect answer.'),
    'dev047':(0.,None,['d0522','d0749'],'The error entry d0522 is retrieved and names acktracker.max_retries, but its configuration page d0749 with Default 20 is absent. The model cannot establish the numeric default from the retrieved forum replies. Judge correctness 0 for abstention is justified; the second retrieval hop failed.')
}


def main():
    questions={q['id']:q for q in load_jsonl(HERE/'data/questions_dev.jsonl')}
    answers={a['id']:a for a in load_jsonl(HERE/'results/answers_r5.jsonl')}
    decisions={r['id']:r for r in load_jsonl(HERE/'results/judge_r5.jsonl')}
    corpus={d['doc_id']:d for d in load_jsonl(HERE/'data/corpus.jsonl')}
    rows=[]
    for qid,(correct,faith,source_ids,note) in REVIEWS.items():
        q=questions[qid];a=answers[qid];j=decisions[qid]
        # Use the actual relevance groups for the two-hop incident instead of
        # assuming a catalogue document ID from the human-readable error code.
        if qid=='dev025':source_ids=list(dict.fromkeys(sum(q['relevant_doc_ids'],[])))
        rows.append({'id':qid,'configuration':'r5','reviewer':'Parsa',
            'category':q['category'],'question':q['question'],'ground_truth':q['answer'],'answer':a['answer'],
            'judge_correctness':j['correctness'],'review_correctness':correct,
            'judge_faithfulness':j['faithfulness'],'review_faithfulness':faith,
            'agree_correctness':correct==j['correctness'],'agree_faithfulness':faith==j['faithfulness'],
            'explanation':note,'evidence_doc_ids':source_ids,
            'evidence_documents':[corpus[d] for d in source_ids], 'contexts':a['contexts']})
    write_jsonl(HERE/'results/judge_review_10.jsonl',rows)
    print(f'Saved {len(rows)} source-checked decisions; correctness agreement {sum(r["agree_correctness"] for r in rows)}/{len(rows)}.')


if __name__=='__main__':main()
