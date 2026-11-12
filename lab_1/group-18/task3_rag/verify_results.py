"""Validate complete outputs and reproduce saved retrieval metrics offline."""
import json
from pathlib import Path

from task3_rag.evaluate import evaluate, load_jsonl
from task3_rag.judge import stratified_sample

HERE=Path(__file__).resolve().parent
R=HERE/'results'


def main():
    dev=load_jsonl(HERE/'data/questions_dev.jsonl')
    test=load_jsonl(HERE/'data/questions_test.jsonl')
    docs={r['doc_id'] for r in load_jsonl(HERE/'data/corpus.jsonl')}
    split=json.loads((R/'split.json').read_text())
    tuning=set(split['tuning_ids']); heldout=set(split['heldout_ids'])
    assert not tuning & heldout and tuning | heldout == {q['id'] for q in dev}
    for config in ('r1','r2','r3_120','r3_220','r3_360','r3','r4','r5'):
        rows=load_jsonl(R/f'retrieval_{config}.jsonl')
        assert len(rows)==len(dev) and {r['id'] for r in rows}=={q['id'] for q in dev}
        for r in rows:
            assert len(r['retrieved_doc_ids'])==len(set(r['retrieved_doc_ids']))==5
            assert set(r['retrieved_doc_ids']) <= docs
            assert len(r['contexts'])==len(r['chunk_ids'])==5
            assert all(cid.startswith(did+':') for cid,did in zip(r['chunk_ids'],r['retrieved_doc_ids']))
        for label,qs in [('all_dev',dev),('tuning',[q for q in dev if q['id'] in tuning]),('heldout',[q for q in dev if q['id'] in heldout])]:
            assert evaluate(rows,qs,5)==json.loads((R/f'metrics_{config}_{label}.json').read_text())
    sample_ids={q['id'] for q in stratified_sample(dev,50)}
    ranking=json.loads((R/'ranking.json').read_text())
    for config in ranking['end_to_end']:
        answers=load_jsonl(R/f'answers_{config}.jsonl')
        judges=load_jsonl(R/f'judge_{config}.jsonl')
        assert len(answers)==len(judges)==50
        assert {r['id'] for r in answers}=={r['id'] for r in judges}==sample_ids
        source={r['id']:r for r in load_jsonl(R/f'retrieval_{config}.jsonl')}
        assert all(a['contexts']==source[a['id']]['contexts'] for a in answers)
    pred=load_jsonl(HERE/'predictions_test.jsonl')
    assert len(pred)==len(test)==100 and {r['id'] for r in pred}=={q['id'] for q in test}
    best=json.loads((R/'best.json').read_text())['configuration']
    raw=load_jsonl(R/f'answers_{best}_test.jsonl')
    assert pred==[{k:a[k] for k in ('id','answer','retrieved_doc_ids')} for a in raw]
    for r in pred:
        assert set(r)=={'id','answer','retrieved_doc_ids'} and r['answer'].strip()
        assert len(r['retrieved_doc_ids'])==len(set(r['retrieved_doc_ids']))==5
        assert set(r['retrieved_doc_ids'])<=docs
    print('Verified: all metric files reproduce; two complete 50-question judge runs; exact contexts; 100 valid test predictions.')


if __name__=='__main__':main()
